"""
Trading service for AI agents to interact with the exchange directly.
These functions are designed to be used as tool calls in LangGraph agents.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from database import get_db_transaction
from database.repositories import (
    LedgerRepository,
    OrderRepository,
    PositionRepository,
    TraderRepository,
)
from engine import order_router
from models.core import CancelReason, OrderStatus, OrderType, Side, Ticker
from models.schemas import OrderRequest
from models.responses import OrderStatusResponse, PortfolioResponse, PositionInfo


async def place_buy_order(
    trader_id: UUID,
    ticker: str,
    quantity: int,
    order_type: OrderType = OrderType.MARKET,
    limit_price_in_cents: Optional[int] = None,
    tif_seconds: int = 60,
) -> UUID:
    """
    Place a BUY order on the exchange.
    
    Args:
        trader_id: UUID of the trader
        ticker: Symbol to buy (e.g., "@elonmusk")
        quantity: Number of shares to buy
        order_type: MARKET, LIMIT, or IOC
        limit_price_in_cents: Max price in cents (required for LIMIT)
        tif_seconds: Time-in-force in seconds
        
    Returns:
        UUID of the created order
    """
    await _validate_buy_order(trader_id, quantity, order_type, limit_price_in_cents)
    return await _submit_order(
        trader_id, ticker, Side.BUY, order_type, quantity, limit_price_in_cents, tif_seconds
    )


async def place_sell_order(
    trader_id: UUID,
    ticker: str,
    quantity: int,
    order_type: OrderType = OrderType.MARKET,
    limit_price_in_cents: Optional[int] = None,
    tif_seconds: int = 60,
) -> UUID:
    """
    Place a SELL order on the exchange.
    
    Args:
        trader_id: UUID of the trader
        ticker: Symbol to sell (e.g., "@elonmusk")
        quantity: Number of shares to sell
        order_type: MARKET, LIMIT, or IOC
        limit_price_in_cents: Min price in cents (required for LIMIT)
        tif_seconds: Time-in-force in seconds
        
    Returns:
        UUID of the created order
    """
    await _validate_sell_order(trader_id, ticker, quantity)
    return await _submit_order(
        trader_id, ticker, Side.SELL, order_type, quantity, limit_price_in_cents, tif_seconds
    )


async def cancel_order(trader_id: UUID, order_id: UUID) -> bool:
    """
    Cancel an existing order.
    
    Args:
        trader_id: UUID of the trader
        order_id: UUID of the order to cancel
        
    Returns:
        True if cancellation submitted, False if not cancellable
    """
    async with get_db_transaction() as session:
        order_repo = OrderRepository(session)
        order = await order_repo.get_order_or_none(order_id)
        
        if not order:
            raise ValueError(f"Order not found: {order_id}")
        
        if order.trader_id != trader_id:
            raise ValueError(f"Order {order_id} not owned by trader {trader_id}")
        
        if order.status not in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
            return False
        
        ticker = order.ticker
    
    await order_router.cancel_order(order_id, ticker, CancelReason.USER)
    return True


async def get_order_status(order_id: UUID) -> OrderStatusResponse:
    """
    Get current status of an order.
    
    Args:
        order_id: UUID of the order
        
    Returns:
        OrderStatusResponse with order details
    """
    async with get_db_transaction() as session:
        order_repo = OrderRepository(session)
        order = await order_repo.get_order_or_none(order_id)
        
        if not order:
            raise ValueError(f"Order not found: {order_id}")
        
        return OrderStatusResponse(
            order_id=order.order_id,
            trader_id=order.trader_id,
            ticker=order.ticker,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            limit_price=order.limit_price,
            filled_quantity=order.filled_quantity,
            status=order.status,
            created_at=order.created_at,
            expires_at=order.expires_at,
        )


async def get_portfolio(trader_id: UUID) -> PortfolioResponse:
    """
    Get trader's current portfolio.
    
    Args:
        trader_id: UUID of the trader
        
    Returns:
        PortfolioResponse with cash balance and positions
    """
    async with get_db_transaction() as session:
        ledger_repo = LedgerRepository(session)
        position_repo = PositionRepository(session)
        
        cash_balance = await ledger_repo.get_cash_balance_in_cents(trader_id)
        positions = await position_repo.get_all_positions(trader_id)
        
        return PortfolioResponse(
            trader_id=trader_id,
            cash_balance_in_cents=cash_balance,
            positions=[
                PositionInfo(
                    ticker=pos.ticker,
                    quantity=pos.quantity,
                    avg_cost_in_cents=pos.avg_cost,
                )
                for pos in positions
            ],
        )


async def create_trader(initial_cash_in_cents: int = 100_000_000) -> UUID:
    """
    Create a new trader with initial cash balance.
    
    Args:
        initial_cash_in_cents: Starting cash in cents (default $1M)
        
    Returns:
        UUID of the created trader
    """
    async with get_db_transaction() as session:
        trader_repo = TraderRepository(session)
        ledger_repo = LedgerRepository(session)
        
        trader = await trader_repo.create_trader_in_transaction_without_commit()
        await ledger_repo.initialize_trader_cash_without_commit(
            trader.trader_id, initial_cash_in_cents
        )
        
        await session.commit()
        return trader.trader_id


# Helper functions (private)


async def _validate_buy_order(
    trader_id: UUID,
    quantity: int,
    order_type: OrderType,
    limit_price_in_cents: Optional[int],
) -> None:
    """Validate buy order has sufficient cash"""
    if order_type == OrderType.LIMIT and limit_price_in_cents is None:
        raise ValueError("Limit price required for LIMIT orders")
    
    async with get_db_transaction() as session:
        trader_repo = TraderRepository(session)
        trader = await trader_repo.get_trader_or_none(trader_id)
        
        if not trader or not trader.is_active:
            raise ValueError(f"Invalid or inactive trader: {trader_id}")
        
        if order_type == OrderType.LIMIT:
            ledger_repo = LedgerRepository(session)
            cash_balance = await ledger_repo.get_cash_balance_in_cents(trader_id)
            required_cash = quantity * limit_price_in_cents
            
            if cash_balance < required_cash:
                raise ValueError(
                    f"Insufficient cash: have ${cash_balance/100:.2f}, "
                    f"need ${required_cash/100:.2f}"
                )


async def _validate_sell_order(
    trader_id: UUID, ticker: str, quantity: int
) -> None:
    """Validate sell order has sufficient shares"""
    Ticker.validate_or_raise(ticker)
    
    async with get_db_transaction() as session:
        position_repo = PositionRepository(session)
        position = await position_repo.get_position_or_none(trader_id, ticker)
        
        if not position or position.quantity < quantity:
            available = position.quantity if position else 0
            raise ValueError(
                f"Insufficient shares of {ticker}: have {available}, need {quantity}"
            )


async def _submit_order(
    trader_id: UUID,
    ticker: str,
    side: Side,
    order_type: OrderType,
    quantity: int,
    limit_price_in_cents: Optional[int],
    tif_seconds: int,
) -> UUID:
    """Submit order to the exchange"""
    Ticker.validate_or_raise(ticker)
    
    order_request = OrderRequest(
        trader_id=trader_id,
        ticker=ticker,
        side=side,
        order_type=order_type,
        quantity=quantity,
        limit_price_in_cents=limit_price_in_cents,
        tif_seconds=tif_seconds,
    )
    
    async with get_db_transaction() as session:
        order_repo = OrderRepository(session)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=tif_seconds)
        order = await order_repo.create_order_without_commit(order_request, expires_at)
        await session.commit()
        order_id = order.order_id
    
    await order_router.submit_order(order_id, ticker)
    return order_id