"""
Traders API endpoints
"""

from datetime import datetime
from typing import List
from uuid import UUID

from database import async_session
from database.repositories import LedgerRepository, TraderRepository, PositionRepository, OrderRepository, TradeRepository
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.core import OrderStatus

router = APIRouter()


class TraderResponse(BaseModel):
    """Trader information"""

    trader_id: UUID
    is_active: bool
    is_admin: bool
    balance_in_cents: int
    created_at: datetime


class PositionInfo(BaseModel):
    """Position information"""
    ticker: str
    quantity: int
    avg_cost: int


class OrderInfo(BaseModel):
    """Order information"""
    order_id: UUID
    ticker: str
    side: str
    order_type: str
    quantity: int
    filled_quantity: int
    limit_price: int | None
    status: str
    created_at: datetime


class TradeInfo(BaseModel):
    """Trade information"""
    trade_id: UUID
    ticker: str
    price: int
    quantity: int
    side: str  # BUY or SELL based on whether trader was buyer or seller
    executed_at: datetime


class TraderDetailResponse(BaseModel):
    """Detailed trader information"""
    trader_id: UUID
    is_active: bool
    is_admin: bool
    balance_in_cents: int
    created_at: datetime
    positions: List[PositionInfo]
    unfilled_orders: List[OrderInfo]
    recent_trades: List[TradeInfo]


@router.get("/", response_model=List[TraderResponse])
async def get_all_traders() -> List[TraderResponse]:
    """
    Get all traders with their current cash balances.
    """
    async with async_session() as session:
        trader_repo = TraderRepository(session)
        ledger_repo = LedgerRepository(session)

        # Get all traders
        traders = await trader_repo.get_all_traders()

        # Build response with balances
        trader_responses = []
        for trader in traders:
            # Get current cash balance
            balance = await ledger_repo.get_cash_balance_in_cents(trader.trader_id)

            trader_responses.append(
                TraderResponse(
                    trader_id=trader.trader_id,
                    is_active=trader.is_active,
                    is_admin=trader.is_admin,
                    balance_in_cents=balance,
                    created_at=trader.created_at,
                )
            )

        return trader_responses


@router.get("/{trader_id}", response_model=TraderDetailResponse)
async def get_trader_detail(trader_id: UUID) -> TraderDetailResponse:
    """
    Get detailed information about a specific trader.
    """
    async with async_session() as session:
        trader_repo = TraderRepository(session)
        ledger_repo = LedgerRepository(session)
        position_repo = PositionRepository(session)
        order_repo = OrderRepository(session)
        trade_repo = TradeRepository(session)

        # Get trader
        trader = await trader_repo.get_trader_or_none(trader_id)
        if not trader:
            raise HTTPException(
                status_code=404, detail=f"Trader not found: {trader_id}"
            )

        # Get current cash balance
        balance = await ledger_repo.get_cash_balance_in_cents(trader.trader_id)
        
        # Get positions
        positions = await position_repo.get_all_positions(trader_id)
        position_info = [
            PositionInfo(
                ticker=pos.ticker,
                quantity=pos.quantity,
                avg_cost=pos.avg_cost
            )
            for pos in positions
        ]
        
        # Get unfilled orders
        unfilled_orders = await order_repo.get_trader_unfilled_orders(trader_id)
        order_info = [
            OrderInfo(
                order_id=order.order_id,
                ticker=order.ticker,
                side=order.side.value,
                order_type=order.order_type.value,
                quantity=order.quantity,
                filled_quantity=order.filled_quantity,
                limit_price=order.limit_price,
                status=order.status.value,
                created_at=order.created_at
            )
            for order in unfilled_orders
        ]
        
        # Get recent trades
        trades = await trade_repo.get_trader_trades(trader_id, limit=50)
        trade_info = [
            TradeInfo(
                trade_id=trade.trade_id,
                ticker=trade.ticker,
                price=trade.price,
                quantity=trade.quantity,
                side="BUY" if trade.buyer_id == trader_id else "SELL",
                executed_at=trade.executed_at
            )
            for trade in trades
        ]

        return TraderDetailResponse(
            trader_id=trader.trader_id,
            is_active=trader.is_active,
            is_admin=trader.is_admin,
            balance_in_cents=balance,
            created_at=trader.created_at,
            positions=position_info,
            unfilled_orders=order_info,
            recent_trades=trade_info
        )
