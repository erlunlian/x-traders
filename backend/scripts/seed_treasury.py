"""Seed a single treasury account and list initial shares for sale.

Actions per ticker:
- Ensure treasury trader exists (single admin via DB constraint)
- Mint 10,000 shares to treasury (ledger + positions)
- Create one LIMIT SELL order for 10,000 shares at $1.00 with long TIF

Usage:
  uv run python backend/scripts/seed_treasury.py
  # or
  python -m backend.scripts.seed_treasury

Note: This script creates orders directly in the database. If the exchange is
running separately, in-memory order books will not reflect these orders until
the next startup (when books are rebuilt) unless those orders are explicitly
submitted to the running engine.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlmodel import select

from config import TICKERS
from database import get_db_transaction
from database.models import LedgerEntry, Position, TraderAccount
from database.repositories import OrderRepository, PositionRepository, TraderRepository
from enums import OrderType, Side
from models.schemas import OrderRequest

LONG_TIF_SECONDS = 365 * 24 * 60 * 60  # 1 year
TREASURY_QUANTITY = 10000
ASK_PRICE_CENTS = 5000  # $50.00
DEFAULT_LADDER_RELATIVE = {
    0.80: 0.05,  # much lower bids
    0.90: 0.10,
    0.95: 0.15,
    0.98: 0.20,
    1.02: 0.20,  # asks above par
    1.05: 0.15,
    1.10: 0.10,
    1.20: 0.05,
}


async def get_or_create_treasury_trader() -> TraderAccount:
    """Return the single admin (treasury) trader, creating it if needed."""
    async with get_db_transaction() as session:
        trader_repo = TraderRepository(session)

        # Find existing admin trader
        result = await session.execute(
            select(TraderAccount).where(TraderAccount.is_admin.is_(True))
        )
        existing: Optional[TraderAccount] = result.scalar_one_or_none()
        if existing:
            return existing

        # Create new admin trader (no need to fund with cash to sell)
        trader = await trader_repo.create_trader_in_transaction_without_commit(is_admin=True)
        await session.commit()
        return trader


async def ensure_treasury_shares(trader: TraderAccount, ticker: str) -> None:
    """Ensure the treasury has exactly TREASURY_QUANTITY shares of ticker.

    Adjust both positions and ledger to reflect the final quantity.
    """
    async with get_db_transaction() as session:
        position_repo = PositionRepository(session)

        current = await position_repo.get_position_or_none(trader.trader_id, ticker)
        current_qty = current.quantity if current else 0
        delta = TREASURY_QUANTITY - current_qty

        if current is None:
            # Create fresh position
            pos = Position(
                trader_id=trader.trader_id,
                ticker=ticker,
                quantity=TREASURY_QUANTITY,
                avg_cost=0,
            )
            session.add(pos)
        else:
            # Update to target quantity
            current.quantity = TREASURY_QUANTITY

        if delta != 0:
            # Adjust ledger share balance to match the target quantity
            if delta > 0:
                # Mint shares into treasury (debit increases balance)
                entry = LedgerEntry(
                    trader_id=trader.trader_id,
                    account=f"SHARES:{ticker}",
                    debit_in_cents=delta,
                    credit_in_cents=0,
                    description=f"Initial issuance: +{delta} {ticker} shares to treasury",
                )
            else:
                # Reduce shares if over target
                entry = LedgerEntry(
                    trader_id=trader.trader_id,
                    account=f"SHARES:{ticker}",
                    debit_in_cents=0,
                    credit_in_cents=abs(delta),
                    description=f"Adjustment: {delta} {ticker} shares from treasury",
                )
            session.add(entry)

        await session.commit()


async def ensure_sell_order(trader: TraderAccount, ticker: str) -> None:
    """Ensure a long-dated LIMIT SELL ladder exists around $1.00 with multiple price levels."""
    async with get_db_transaction() as session:
        order_repo = OrderRepository(session)

        existing_orders = await order_repo.get_trader_unfilled_orders(trader.trader_id)
        existing_prices = {
            (o.side.name, o.limit_price)
            for o in existing_orders
            if o.ticker == ticker and o.order_type == OrderType.LIMIT
        }

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=LONG_TIF_SECONDS)

        # Create ask levels above $1
        for mult, frac in DEFAULT_LADDER_RELATIVE.items():
            if mult <= 1.0:
                continue
            price_cents = int(round(ASK_PRICE_CENTS * mult))
            qty = max(1, int(TREASURY_QUANTITY * frac))
            key = ("SELL", price_cents)
            if key in existing_prices:
                continue
            order_request = OrderRequest(
                trader_id=trader.trader_id,
                ticker=ticker,
                side=Side.SELL,
                order_type=OrderType.LIMIT,
                quantity=qty,
                limit_price_in_cents=price_cents,
                tif_seconds=LONG_TIF_SECONDS,
            )
            await order_repo.create_order_without_commit(order_request, expires_at)
        await session.commit()

    # After commit, if the engine is running and the processor for this ticker exists,
    # submit the order so it appears in the live in-memory order book.
    try:
        from engine import order_router

        # Submit all unfilled treasury limit orders for this ticker
        async with get_db_transaction() as session:
            order_repo = OrderRepository(session)
            open_orders = await order_repo.get_trader_unfilled_orders(trader.trader_id)
            for o in open_orders:
                if o.ticker == ticker and o.order_type == OrderType.LIMIT:
                    await order_router.submit_order(o.order_id, ticker)
    except Exception:
        # Engine not running/initialized; will appear after next startup rebuild
        pass


async def ensure_bid_ladder(trader: TraderAccount, ticker: str) -> None:
    """Post admin BUY ladder to provide initial bid liquidity."""
    from services.trading import place_admin_order

    for mult, frac in DEFAULT_LADDER_RELATIVE.items():
        if mult >= 1.0:
            continue
        price_cents = int(round(ASK_PRICE_CENTS * mult))
        qty = max(1, int(TREASURY_QUANTITY * frac))
        try:
            await place_admin_order(
                trader_id=trader.trader_id,
                ticker=ticker,
                side=Side.BUY,
                order_type=OrderType.LIMIT,
                quantity=qty,
                limit_price_in_cents=price_cents,
                tif_seconds=LONG_TIF_SECONDS,
            )
        except Exception:
            continue


async def has_circulating_shares(ticker: str, treasury: TraderAccount) -> bool:
    """Return True if any non-treasury account holds >0 shares for ticker."""
    async with get_db_transaction() as session:
        result = await session.execute(
            select(Position)
            .where(Position.ticker == ticker)
            .where(Position.quantity > 0)
            .where(Position.trader_id != treasury.trader_id)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None


async def main() -> None:
    trader = await get_or_create_treasury_trader()

    # Seed positions and orders per ticker
    for ticker in TICKERS:
        # Skip if shares are already circulating for this ticker
        if await has_circulating_shares(ticker, trader):
            print(f"Skipping {ticker}: shares already circulating.")
            continue
        await ensure_treasury_shares(trader, ticker)
        await ensure_sell_order(trader, ticker)
        await ensure_bid_ladder(trader, ticker)

    print(
        f"Seeded treasury {trader.trader_id} with {TREASURY_QUANTITY} shares and bid/ask ladders around ${ASK_PRICE_CENTS/100} for {len(TICKERS)} tickers."
    )


if __name__ == "__main__":
    asyncio.run(main())
