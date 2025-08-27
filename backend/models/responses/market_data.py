"""
Response models for market data tools.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class PriceData(BaseModel):
    """Price data for a single ticker"""
    ticker: str
    last_price_dollars: Optional[float] = None
    best_bid_dollars: Optional[float] = None
    best_ask_dollars: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    spread_dollars: Optional[float] = None


class PriceResult(BaseModel):
    """Result for single ticker price query"""
    success: bool
    ticker: Optional[str] = None
    last_price_dollars: Optional[float] = None
    best_bid_dollars: Optional[float] = None
    best_ask_dollars: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    spread_dollars: Optional[float] = None
    error: Optional[str] = None


class AllPricesResult(BaseModel):
    """Result for all tickers price query"""
    success: bool
    prices: List[PriceData] = Field(default_factory=list)
    error: Optional[str] = None


class OrderBookLevelData(BaseModel):
    """Single price level in order book"""
    price_dollars: float
    quantity: int


class OrderBookData(BaseModel):
    """Order book data result"""
    success: bool
    ticker: Optional[str] = None
    bids: List[OrderBookLevelData] = Field(default_factory=list)
    asks: List[OrderBookLevelData] = Field(default_factory=list)
    last_price_dollars: Optional[float] = None
    error: Optional[str] = None


class TradeData(BaseModel):
    """Single trade data"""
    price_dollars: float
    quantity: int
    time: str  # ISO format string


class RecentTradesData(BaseModel):
    """Recent trades data result"""
    success: bool
    ticker: Optional[str] = None
    trades: List[TradeData] = Field(default_factory=list)
    error: Optional[str] = None


class TickerListResult(BaseModel):
    """Result for ticker list query"""
    success: bool
    tickers: List[str] = Field(default_factory=list)
    error: Optional[str] = None