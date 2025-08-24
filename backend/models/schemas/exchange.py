from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.core import MarketDataEventType, OrderType, Side


class OrderRequest(BaseModel):
    """Request to create an order"""

    trader_id: UUID
    ticker: str
    side: Side
    order_type: OrderType
    quantity: int = Field(gt=0)
    limit_price_in_cents: Optional[int] = Field(None, gt=0)
    tif_seconds: int = Field(60, gt=0)  # Default 60 seconds

    model_config = ConfigDict(use_enum_values=True)


class TradeData(BaseModel):
    """Trade execution data"""

    buy_order_id: UUID
    sell_order_id: UUID
    ticker: str
    price_in_cents: int = Field(gt=0)
    quantity: int = Field(gt=0)
    buyer_id: UUID
    seller_id: UUID
    taker_order_id: UUID
    maker_order_id: UUID
    executed_at: Optional[datetime] = None


class BookState(BaseModel):
    """Current state of order book for market data"""

    best_bid_in_cents: Optional[int] = None
    best_ask_in_cents: Optional[int] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None


class MarketDataEvent(BaseModel):
    """Event for market data outbox"""

    event_type: MarketDataEventType
    ticker: str
    trade: Optional[TradeData] = None
    book: Optional[BookState] = None
    timestamp: datetime

    model_config = ConfigDict(use_enum_values=True)


class OrderBookSnapshot(BaseModel):
    """Order book snapshot for API responses"""

    ticker: str
    bids: Dict[int, int]  # price_in_cents -> total_quantity
    asks: Dict[int, int]  # price_in_cents -> total_quantity
    last_price_in_cents: Optional[int] = None
    timestamp: datetime


class Position(BaseModel):
    """Trader position"""

    trader_id: UUID
    ticker: str
    quantity: int
    avg_cost_in_cents: int
    market_value_in_cents: Optional[int] = None
    unrealized_pnl_in_cents: Optional[int] = None


class Portfolio(BaseModel):
    """Trader portfolio"""

    trader_id: UUID
    cash_balance_in_cents: int
    positions: List[Position]
    total_value_in_cents: int
