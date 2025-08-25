from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from models.core import OrderType, Side
from pydantic import BaseModel
from services.trading import create_trader, place_admin_order

router = APIRouter()


class CreateTraderResponse(BaseModel):
    trader_id: UUID


@router.post("/trader", response_model=CreateTraderResponse)
async def admin_create_trader(initial_cash_in_cents: int = 1_000_000_000_000):
    """
    Create a trader for admin usage with a very large initial cash balance.
    """
    trader_id = await create_trader(initial_cash_in_cents=initial_cash_in_cents)
    return CreateTraderResponse(trader_id=trader_id)


class AdminOrderRequest(BaseModel):
    trader_id: UUID
    ticker: str
    side: Side
    order_type: OrderType = OrderType.MARKET
    quantity: int
    limit_price_in_cents: Optional[int] = None
    tif_seconds: int = 60


class AdminOrderResponse(BaseModel):
    order_id: UUID


@router.post("/order", response_model=AdminOrderResponse)
async def admin_place_order(req: AdminOrderRequest):
    """
    Place an admin order. Unlimited cash for BUY, but SELL still requires shares.
    """
    try:
        order_id = await place_admin_order(
            trader_id=req.trader_id,
            ticker=req.ticker,
            side=req.side,
            order_type=req.order_type,
            quantity=req.quantity,
            limit_price_in_cents=req.limit_price_in_cents,
            tif_seconds=req.tif_seconds,
        )
        return AdminOrderResponse(order_id=order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
