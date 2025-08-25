import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from enums import CancelReason, MarketDataEventType, OrderStatus
from models.schemas import BookState, OrderRequest, TradeData
from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    DBLedgerEntry,
    DBMarketDataOutbox,
    DBOrder,
    DBPosition,
    DBSequenceCounter,
    DBTrade,
    DBTraderAccount,
)


class OrderRepository:
    """
    Repository for order operations.
    Note: Methods do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_next_sequence(self, ticker: str) -> int:
        """Atomic UPSERT for sequence - handles race on first insert"""
        stmt = (
            insert(DBSequenceCounter)
            .values(ticker=ticker, last_sequence=1)
            .on_conflict_do_update(
                index_elements=["ticker"],
                set_={"last_sequence": DBSequenceCounter.last_sequence + 1},
            )
            .returning(DBSequenceCounter.last_sequence)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create_order_without_commit(
        self, order_request: OrderRequest, expires_at: datetime
    ) -> DBOrder:
        """
        Create order with sequence number.
        Must be called within a transaction context - does NOT commit.
        """
        sequence = await self.get_next_sequence(order_request.ticker)

        order = DBOrder(
            trader_id=order_request.trader_id,
            ticker=order_request.ticker,
            side=order_request.side,
            order_type=order_request.order_type,
            quantity=order_request.quantity,
            limit_price=order_request.limit_price_in_cents,
            filled_quantity=0,
            status=OrderStatus.PENDING,
            sequence=sequence,
            tif_seconds=order_request.tif_seconds,
            expires_at=expires_at,
        )
        self.session.add(order)
        await self.session.flush()  # Get ID but stay in transaction
        return order

    async def get_order(self, order_id: uuid.UUID) -> DBOrder:
        """Get order by ID - raises if not found"""
        result = await self.session.execute(
            select(DBOrder).where(DBOrder.order_id == order_id)
        )
        return result.scalar_one()

    async def get_order_or_none(self, order_id: uuid.UUID) -> Optional[DBOrder]:
        """Get order by ID - returns None if not found"""
        result = await self.session.execute(
            select(DBOrder).where(DBOrder.order_id == order_id)
        )
        return result.scalar_one_or_none()

    async def update_filled_without_commit(
        self, order_id: uuid.UUID, fill_quantity: int
    ):
        """
        Update order filled quantity and status.
        Validates that filled quantity doesn't exceed order quantity.
        """
        result = await self.session.execute(
            select(DBOrder).where(DBOrder.order_id == order_id).with_for_update()
        )
        order = result.scalar_one()

        new_filled = order.filled_quantity + fill_quantity
        if new_filled > order.quantity:
            raise ValueError(
                f"Fill quantity {new_filled} exceeds order quantity {order.quantity}"
            )

        order.filled_quantity = new_filled

        # Update status based on fill
        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
        elif order.filled_quantity > 0:
            order.status = OrderStatus.PARTIAL
        # else stays PENDING

    async def get_unfilled_orders(self, ticker: str) -> List[DBOrder]:
        """Get all unfilled orders for building order book"""
        result = await self.session.execute(
            select(DBOrder)
            .where(DBOrder.ticker == ticker)
            .where(DBOrder.status.in_([OrderStatus.PENDING, OrderStatus.PARTIAL]))
            .order_by(DBOrder.sequence)
        )
        return result.scalars().all()

    async def get_trader_unfilled_orders(self, trader_id: uuid.UUID) -> List[DBOrder]:
        """Get all unfilled orders for a specific trader"""
        result = await self.session.execute(
            select(DBOrder)
            .where(DBOrder.trader_id == trader_id)
            .where(DBOrder.status.in_([OrderStatus.PENDING, OrderStatus.PARTIAL]))
            .order_by(DBOrder.created_at.desc())
        )
        return result.scalars().all()

    async def get_expired_orders(self, limit: int = 100) -> List[DBOrder]:
        """Get orders that have exceeded their TIF"""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        result = await self.session.execute(
            select(DBOrder)
            .where(DBOrder.expires_at <= now)
            .where(DBOrder.status.in_([OrderStatus.PENDING, OrderStatus.PARTIAL]))
            .limit(limit)
        )
        return result.scalars().all()

    async def cancel_order_without_commit(
        self, order_id: uuid.UUID, cancel_reason: CancelReason
    ) -> DBOrder:
        """
        Cancel an order with the specified reason.
        Must be called within a transaction context - does NOT commit.
        Raises if order not found.
        """

        order = await self.get_order(order_id)  # Will raise if not found

        # Only cancel if order is still active
        if order.status not in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
            raise ValueError(
                f"Cannot cancel order {order_id} with status {order.status}"
            )

        # Update status based on reason
        if cancel_reason == CancelReason.USER:
            order.status = OrderStatus.CANCELLED
        else:
            order.status = OrderStatus.EXPIRED

        order.cancel_reason = cancel_reason
        return order


class TradeRepository:
    """
    Repository for trade operations.
    Note: Methods do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_trade_without_commit(self, trade_data: TradeData) -> DBTrade:
        """
        Record trade execution.
        Must be called within a transaction context - does NOT commit.
        """
        trade = DBTrade(
            buy_order_id=trade_data.buy_order_id,
            sell_order_id=trade_data.sell_order_id,
            ticker=trade_data.ticker,
            price=trade_data.price_in_cents,
            quantity=trade_data.quantity,
            buyer_id=trade_data.buyer_id,
            seller_id=trade_data.seller_id,
            taker_order_id=trade_data.taker_order_id,
            maker_order_id=trade_data.maker_order_id,
            executed_at=trade_data.executed_at or datetime.now(timezone.utc),
        )
        self.session.add(trade)
        await self.session.flush()
        return trade

    async def get_recent_trades(self, ticker: str, limit: int = 50) -> List[DBTrade]:
        result = await self.session.execute(
            select(DBTrade)
            .where(DBTrade.ticker == ticker)
            .order_by(DBTrade.executed_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_trader_trades(self, trader_id: uuid.UUID, limit: int = 50) -> List[DBTrade]:
        """Get recent trades for a specific trader (as buyer or seller)"""
        from sqlalchemy import or_
        
        result = await self.session.execute(
            select(DBTrade)
            .where(or_(DBTrade.buyer_id == trader_id, DBTrade.seller_id == trader_id))
            .order_by(DBTrade.executed_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_ohlc_history(
        self, ticker: str, interval: str, periods: int
    ) -> List[Dict]:
        """
        Get OHLC (Open, High, Low, Close) data for a ticker.

        Args:
            ticker: The ticker symbol
            interval: PostgreSQL interval string (e.g., '1 hour', '1 day', '1 week')
            periods: Number of periods to return

        Returns:
            List of dicts with timestamp, open, high, low, close, volume
        """
        from datetime import datetime, timedelta, timezone

        # Determine time window and truncation
        now = datetime.now(timezone.utc)
        if interval == "1 hour":
            start_time = now - timedelta(hours=periods)
            trunc = "hour"
        elif interval == "6 hours":
            start_time = now - timedelta(hours=periods * 6)
            trunc = "hour"  # Still truncate by hour, but we'll group by 6-hour periods
        elif interval == "1 day":
            start_time = now - timedelta(days=periods)
            trunc = "day"
        elif interval == "1 week":
            start_time = now - timedelta(weeks=periods)
            trunc = "week"
        else:
            # Default fallback
            start_time = now - timedelta(days=30)
            trunc = "day"

        # Simpler query using GROUP BY instead of window functions for the main aggregation
        from sqlalchemy import text

        query = text(
            """
            WITH time_periods AS (
                SELECT 
                    date_trunc(:trunc, executed_at) AS period,
                    MIN(executed_at) AS first_trade_time,
                    MAX(executed_at) AS last_trade_time
                FROM trades
                WHERE ticker = :ticker
                    AND executed_at >= :start_time
                GROUP BY date_trunc(:trunc, executed_at)
            ),
            period_ohlc AS (
                SELECT 
                    tp.period,
                    -- Get first trade price (open)
                    (SELECT price FROM trades 
                     WHERE ticker = :ticker 
                       AND executed_at = tp.first_trade_time 
                     LIMIT 1) AS open,
                    -- Get last trade price (close)
                    (SELECT price FROM trades 
                     WHERE ticker = :ticker 
                       AND executed_at = tp.last_trade_time 
                     LIMIT 1) AS close,
                    -- Get high/low/volume for the period
                    MAX(t.price) AS high,
                    MIN(t.price) AS low,
                    SUM(t.quantity) AS volume
                FROM time_periods tp
                JOIN trades t ON t.ticker = :ticker 
                    AND date_trunc(:trunc, t.executed_at) = tp.period
                GROUP BY tp.period, tp.first_trade_time, tp.last_trade_time
            )
            SELECT 
                period AS timestamp,
                open,
                high,
                low,
                close,
                volume
            FROM period_ohlc
            ORDER BY period ASC
        """
        )

        result = await self.session.execute(
            query,
            {
                "ticker": ticker,
                "trunc": trunc,
                "start_time": start_time,
            },
        )

        rows = result.fetchall()

        # Convert to list of dicts
        ohlc_data = []
        for row in rows:
            ohlc_data.append(
                {
                    "timestamp": row.timestamp,
                    "open": row.open,
                    "high": row.high,
                    "low": row.low,
                    "close": row.close,
                    "volume": int(row.volume) if row.volume else 0,
                }
            )

        # If we need to group 6-hour periods, do it in Python
        if interval == "6 hours":
            grouped_data = []
            i = 0
            while i < len(ohlc_data):
                # Take up to 6 hourly candles and combine them
                group = ohlc_data[i : min(i + 6, len(ohlc_data))]
                if group:
                    grouped_data.append(
                        {
                            "timestamp": group[0]["timestamp"],
                            "open": group[0]["open"],
                            "high": max(g["high"] for g in group),
                            "low": min(g["low"] for g in group),
                            "close": group[-1]["close"],
                            "volume": sum(g["volume"] for g in group),
                        }
                    )
                i += 6
            ohlc_data = grouped_data

        return ohlc_data


class PositionRepository:
    """
    Repository for position tracking.
    Note: Methods do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_for_buy_without_commit(
        self, trader_id: uuid.UUID, ticker: str, quantity: int, price_in_cents: int
    ):
        """Update position and avg_cost for buy"""
        # Get current position with lock
        result = await self.session.execute(
            select(DBPosition)
            .where(and_(DBPosition.trader_id == trader_id, DBPosition.ticker == ticker))
            .with_for_update()
        )
        position = result.scalar_one_or_none()

        if position:
            # Update avg_cost: (old_qty * old_avg + new_qty * price) / total_qty
            new_qty = position.quantity + quantity
            new_avg = (
                ((position.quantity * position.avg_cost) + (quantity * price_in_cents))
                // new_qty
                if new_qty > 0
                else 0
            )

            position.quantity = new_qty
            position.avg_cost = new_avg
        else:
            # Create new position
            position = DBPosition(
                trader_id=trader_id,
                ticker=ticker,
                quantity=quantity,
                avg_cost=price_in_cents,
            )
            self.session.add(position)

    async def update_for_sell_without_commit(
        self, trader_id: uuid.UUID, ticker: str, quantity: int
    ):
        """Update position for sell - avg_cost remains unchanged"""
        result = await self.session.execute(
            select(DBPosition)
            .where(and_(DBPosition.trader_id == trader_id, DBPosition.ticker == ticker))
            .with_for_update()
        )
        position = result.scalar_one_or_none()

        if not position or position.quantity < quantity:
            raise ValueError(
                f"Insufficient shares: trying to sell {quantity}, have {position.quantity if position else 0}"
            )

        position.quantity -= quantity

    async def get_position(self, trader_id: uuid.UUID, ticker: str) -> DBPosition:
        """Get position - raises if not found"""
        result = await self.session.execute(
            select(DBPosition).where(
                and_(DBPosition.trader_id == trader_id, DBPosition.ticker == ticker)
            )
        )
        return result.scalar_one()

    async def get_position_or_none(
        self, trader_id: uuid.UUID, ticker: str
    ) -> Optional[DBPosition]:
        """Get position - returns None if not found"""
        result = await self.session.execute(
            select(DBPosition).where(
                and_(DBPosition.trader_id == trader_id, DBPosition.ticker == ticker)
            )
        )
        return result.scalar_one_or_none()

    async def get_all_positions(self, trader_id: uuid.UUID) -> List[DBPosition]:
        """Get all positions for a trader"""
        result = await self.session.execute(
            select(DBPosition)
            .where(DBPosition.trader_id == trader_id)
            .where(DBPosition.quantity > 0)
        )
        return result.scalars().all()


class LedgerRepository:
    """
    Repository for double-entry bookkeeping.
    Note: Methods do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def post_trade_entries_without_commit(self, trade: DBTrade):
        """Post double-entry for trade execution"""
        # Cash entries
        cash_entries = [
            DBLedgerEntry(
                trade_id=trade.trade_id,
                trader_id=trade.buyer_id,
                account="CASH",
                debit_in_cents=trade.price * trade.quantity,
                credit_in_cents=0,
                description=f"Buy {trade.quantity} {trade.ticker} @ ${trade.price/100:.2f}",
            ),
            DBLedgerEntry(
                trade_id=trade.trade_id,
                trader_id=trade.seller_id,
                account="CASH",
                debit_in_cents=0,
                credit_in_cents=trade.price * trade.quantity,
                description=f"Sell {trade.quantity} {trade.ticker} @ ${trade.price/100:.2f}",
            ),
        ]

        # Share entries (stored as quantity, not cents)
        share_entries = [
            DBLedgerEntry(
                trade_id=trade.trade_id,
                trader_id=trade.buyer_id,
                account=f"SHARES:{trade.ticker}",
                debit_in_cents=trade.quantity,  # Using cents field for quantity
                credit_in_cents=0,
                description=f"Receive {trade.quantity} shares",
            ),
            DBLedgerEntry(
                trade_id=trade.trade_id,
                trader_id=trade.seller_id,
                account=f"SHARES:{trade.ticker}",
                debit_in_cents=0,
                credit_in_cents=trade.quantity,  # Using cents field for quantity
                description=f"Deliver {trade.quantity} shares",
            ),
        ]

        for entry in cash_entries + share_entries:
            self.session.add(entry)

    async def get_cash_balance_in_cents(self, trader_id: uuid.UUID) -> int:
        """Get current cash balance in cents"""
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(DBLedgerEntry.debit_in_cents), 0)
                - func.coalesce(func.sum(DBLedgerEntry.credit_in_cents), 0)
            )
            .where(DBLedgerEntry.trader_id == trader_id)
            .where(DBLedgerEntry.account == "CASH")
        )
        return result.scalar() or 0

    async def get_share_balance(self, trader_id: uuid.UUID, ticker: str) -> int:
        """Get share balance (quantity, not cents)"""
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(DBLedgerEntry.debit_in_cents), 0)
                - func.coalesce(func.sum(DBLedgerEntry.credit_in_cents), 0)
            )
            .where(DBLedgerEntry.trader_id == trader_id)
            .where(DBLedgerEntry.account == f"SHARES:{ticker}")
        )
        return result.scalar() or 0

    async def initialize_trader_cash_without_commit(
        self, trader_id: uuid.UUID, initial_cash_in_cents: int
    ):
        """
        Give trader starting cash.
        Must be called within a transaction context - does NOT commit.
        """
        entry = DBLedgerEntry(
            trader_id=trader_id,
            account="CASH",
            debit_in_cents=initial_cash_in_cents,
            credit_in_cents=0,
            description=f"Initial deposit: ${initial_cash_in_cents/100:.2f}",
        )
        self.session.add(entry)


class OutboxRepository:
    """
    Repository for market data outbox pattern.
    Note: Methods do NOT commit except publish_batch which is autonomous.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def queue_trade_event_without_commit(
        self, trade_data: TradeData, book_state: BookState
    ):
        """
        Queue trade event with book state.
        Does NOT commit - must be called within trade transaction.
        """
        event = DBMarketDataOutbox(
            event_type=MarketDataEventType.TRADE,
            ticker=trade_data.ticker,
            payload={
                "trade": {
                    "price_in_cents": trade_data.price_in_cents,
                    "quantity": trade_data.quantity,
                    "timestamp": (
                        trade_data.executed_at or datetime.now(timezone.utc)
                    ).isoformat(),
                },
                "book": {
                    "best_bid_in_cents": book_state.best_bid_in_cents,
                    "best_ask_in_cents": book_state.best_ask_in_cents,
                    "bid_size": book_state.bid_size,
                    "ask_size": book_state.ask_size,
                },
            },
        )
        self.session.add(event)

    async def publish_batch_with_commit(
        self, redis_client=None, limit: int = 100
    ) -> int:
        """
        Atomically claim and publish outbox events.
        This DOES commit as it's a separate autonomous transaction.
        Uses skip_locked to allow multiple workers without contention.
        """
        # Use FOR UPDATE SKIP LOCKED to avoid contention between workers
        result = await self.session.execute(
            select(DBMarketDataOutbox)
            .where(~DBMarketDataOutbox.published)
            .order_by(DBMarketDataOutbox.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)  # Skip rows locked by other workers
        )
        events = result.scalars().all()

        if events and redis_client:
            # Publish to Redis/WebSocket
            for event in events:
                channel = f"{event.event_type.value.lower()}.{event.ticker}"
                await redis_client.publish(channel, event.payload)

            # Mark as published
            event_ids = [e.event_id for e in events]
            await self.session.execute(
                update(DBMarketDataOutbox)
                .where(DBMarketDataOutbox.event_id.in_(event_ids))
                .values(published=True)
            )
            await self.session.commit()  # Autonomous commit for outbox

        return len(events)


class TraderRepository:
    """
    Repository for trader accounts.
    Note: Methods do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_trader_in_transaction_without_commit(
        self,
        trader_id: Optional[uuid.UUID] = None,
        is_admin: bool = False,
    ) -> DBTraderAccount:
        """
        Create a new trader account.
        Must be called within a transaction context - does NOT commit.
        """
        trader = DBTraderAccount(
            trader_id=trader_id or uuid.uuid4(),
            is_active=True,
            is_admin=is_admin,
        )
        self.session.add(trader)
        await self.session.flush()
        return trader

    async def get_trader(self, trader_id: uuid.UUID) -> DBTraderAccount:
        """Get trader - raises if not found"""
        result = await self.session.execute(
            select(DBTraderAccount).where(DBTraderAccount.trader_id == trader_id)
        )
        return result.scalar_one()

    async def get_trader_or_none(
        self, trader_id: uuid.UUID
    ) -> Optional[DBTraderAccount]:
        """Get trader - returns None if not found"""
        result = await self.session.execute(
            select(DBTraderAccount).where(DBTraderAccount.trader_id == trader_id)
        )
        return result.scalar_one_or_none()

    async def get_all_traders(self) -> List[DBTraderAccount]:
        """Get all traders"""
        result = await self.session.execute(
            select(DBTraderAccount)
            .where(DBTraderAccount.is_active)
            .order_by(DBTraderAccount.created_at.desc())
        )
        return result.scalars().all()
