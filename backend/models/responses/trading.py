"""
Models for trading service responses
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from enums import OrderStatus, OrderType, Side


class OrderStatusResponse(BaseModel):
    """Response for order status query"""

    order_id: UUID
    trader_id: UUID
    ticker: str
    side: Side
    order_type: OrderType
    quantity: int
    limit_price: Optional[int]
    filled_quantity: int
    status: OrderStatus
    created_at: datetime
    expires_at: datetime


class PositionInfo(BaseModel):
    """Position information"""

    ticker: str
    quantity: int
    avg_cost_in_cents: int


class PortfolioResponse(BaseModel):
    """Portfolio information"""

    trader_id: UUID
    cash_balance_in_cents: int
    positions: List[PositionInfo]


class OrderResult(BaseModel):
    """Result of placing an order"""

    success: bool
    order_id: Optional[UUID] = None
    message: str
    error: Optional[str] = None


class CancelResult(BaseModel):
    """Result of cancelling an order"""

    success: bool
    message: str
    error: Optional[str] = None


class OrderStatusResult(BaseModel):
    """Result of checking order status"""

    success: bool
    order_id: Optional[UUID] = None
    ticker: Optional[str] = None
    side: Optional[str] = None
    quantity: Optional[int] = None
    filled_quantity: Optional[int] = None
    status: Optional[str] = None
    limit_price: Optional[int] = None
    error: Optional[str] = None


class PortfolioResult(BaseModel):
    """Result of checking portfolio"""

    success: bool
    cash_balance_dollars: Optional[float] = None
    positions: Optional[List[dict]] = None
    error: Optional[str] = None


class TraderResult(BaseModel):
    """Result of creating a trader"""

    success: bool
    trader_id: Optional[UUID] = None
    initial_cash_dollars: Optional[float] = None
    error: Optional[str] = None


class PriceInfo(BaseModel):
    """Current price information for a ticker"""

    ticker: str
    last_price_in_cents: Optional[int]
    current_price_in_cents: Optional[int]
    best_bid_in_cents: Optional[int]
    best_ask_in_cents: Optional[int]
    bid_size: Optional[int]
    ask_size: Optional[int]
    spread_in_cents: Optional[int]


class OrderBookLevel(BaseModel):
    """Single price level in order book"""

    price_in_cents: int
    quantity: int


class OrderBookResult(BaseModel):
    """Order book snapshot result"""

    success: bool
    ticker: Optional[str] = None
    bids: List[OrderBookLevel] = Field(default_factory=list)
    asks: List[OrderBookLevel] = Field(default_factory=list)
    last_price_in_cents: Optional[int] = None
    current_price_in_cents: Optional[int] = None
    error: Optional[str] = None


class TradeInfo(BaseModel):
    """Trade information"""

    trade_id: UUID
    ticker: str
    price_in_cents: int
    quantity: int
    executed_at: datetime


class RecentTradesResult(BaseModel):
    """Recent trades result"""

    success: bool
    ticker: Optional[str] = None
    trades: List[TradeInfo] = Field(default_factory=list)
    error: Optional[str] = None
