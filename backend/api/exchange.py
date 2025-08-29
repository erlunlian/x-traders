"""
Exchange API endpoints for market data (read-only)
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from database import async_session
from database.repositories import TradeRepository
from engine import order_router
from models.schemas import OrderBookSnapshot

router = APIRouter()


class TradeResponse(BaseModel):
    """Trade information"""

    trade_id: UUID
    ticker: str
    price_in_cents: int
    quantity: int
    buyer_id: UUID
    seller_id: UUID
    executed_at: datetime


class CurrentPrice(BaseModel):
    """Current price information"""

    ticker: str
    current_price_in_cents: Optional[int]
    best_bid_in_cents: Optional[int]
    best_ask_in_cents: Optional[int]
    bid_size: Optional[int]
    ask_size: Optional[int]
    timestamp: datetime


@router.get("/price/{ticker}", response_model=CurrentPrice)
async def get_current_price(ticker: str) -> CurrentPrice:
    """
    Get current price and best bid/ask for a ticker.
    """
    if ticker not in order_router.get_tickers():
        raise HTTPException(status_code=404, detail=f"Ticker not found: {ticker}")

    snapshot = order_router.get_order_book(ticker)

    # Get best bid/ask from order book
    best_bid_in_cents = max(snapshot.bids.keys()) if snapshot.bids else None
    best_ask_in_cents = min(snapshot.asks.keys()) if snapshot.asks else None
    bid_size = snapshot.bids.get(best_bid_in_cents)
    ask_size = snapshot.asks.get(best_ask_in_cents)

    return CurrentPrice(
        ticker=ticker,
        current_price_in_cents=snapshot.current_price_in_cents,
        best_bid_in_cents=best_bid_in_cents,
        best_ask_in_cents=best_ask_in_cents,
        bid_size=bid_size,
        ask_size=ask_size,
        timestamp=snapshot.timestamp,
    )


@router.get("/prices", response_model=List[CurrentPrice])
async def get_all_prices() -> List[CurrentPrice]:
    """
    Get current prices for all tickers.
    """
    prices = []
    for ticker in order_router.get_tickers():
        snapshot = order_router.get_order_book(ticker)

        best_bid_in_cents = max(snapshot.bids.keys()) if snapshot.bids else None
        best_ask_in_cents = min(snapshot.asks.keys()) if snapshot.asks else None
        bid_size = snapshot.bids.get(best_bid_in_cents)
        ask_size = snapshot.asks.get(best_ask_in_cents)

        prices.append(
            CurrentPrice(
                ticker=ticker,
                current_price_in_cents=snapshot.current_price_in_cents,
                best_bid_in_cents=best_bid_in_cents,
                best_ask_in_cents=best_ask_in_cents,
                bid_size=bid_size,
                ask_size=ask_size,
                timestamp=snapshot.timestamp,
            )
        )

    return prices


@router.get("/trades/{ticker}", response_model=List[TradeResponse])
async def get_recent_trades(
    ticker: str,
    limit: int = Query(50, ge=1, le=500, description="Number of trades to return"),
) -> List[TradeResponse]:
    """
    Get recent trades for a ticker.
    Returns trades in descending order (most recent first).
    """
    if ticker not in order_router.get_tickers():
        raise HTTPException(status_code=404, detail=f"Ticker not found: {ticker}")

    async with async_session() as session:
        trade_repo = TradeRepository(session)
        trades = await trade_repo.get_recent_trades(ticker, limit)

        return [
            TradeResponse(
                trade_id=trade.trade_id,
                ticker=trade.ticker,
                price_in_cents=trade.price,
                quantity=trade.quantity,
                buyer_id=trade.buyer_id,
                seller_id=trade.seller_id,
                executed_at=trade.executed_at,
            )
            for trade in trades
        ]


@router.get("/orderbook/{ticker}", response_model=OrderBookSnapshot)
async def get_order_book(ticker: str) -> OrderBookSnapshot:
    """
    Get current order book snapshot for a ticker.
    Returns aggregated view of all orders at each price level.
    """
    if ticker not in order_router.get_tickers():
        raise HTTPException(status_code=404, detail=f"Ticker not found: {ticker}")

    snapshot = order_router.get_order_book(ticker)
    return snapshot


class PriceHistoryPoint(BaseModel):
    """Price history data point"""

    timestamp: datetime
    open: int
    high: int
    low: int
    close: int
    volume: int


@router.get("/price-history/{ticker}", response_model=List[PriceHistoryPoint])
async def get_price_history(
    ticker: str,
    time_range: str = Query("1d", description="Time range: 1d, 1w, 1m, 6m, 1y", alias="range"),
) -> List[PriceHistoryPoint]:
    """
    Get price history for a ticker aggregated into OHLC format.
    Returns real trade data aggregated into candlestick format.
    """
    if ticker not in order_router.get_tickers():
        raise HTTPException(status_code=404, detail=f"Ticker not found: {ticker}")

    # Map time ranges to PostgreSQL intervals and number of periods
    range_config = {
        "1d": ("1 hour", 24),  # 24 hourly candles for last day
        "1w": ("6 hours", 28),  # 28 6-hour candles for last week
        "1m": ("1 day", 30),  # 30 daily candles for last month
        "6m": ("1 week", 26),  # 26 weekly candles for last 6 months
        "1y": ("1 week", 52),  # 52 weekly candles for last year
    }

    # Get interval and periods, default to 1 day if invalid range
    interval, periods = range_config.get(time_range, ("1 hour", 24))

    # Get OHLC data from database
    async with async_session() as session:
        trade_repo = TradeRepository(session)
        ohlc_data = await trade_repo.get_ohlc_history(ticker, interval, periods)

    # If no data, return empty array (no trades yet)
    if not ohlc_data:
        return []

    # Convert to response format
    history = []
    for candle in ohlc_data:
        history.append(
            PriceHistoryPoint(
                timestamp=candle["timestamp"],
                open=candle["open"],
                high=candle["high"],
                low=candle["low"],
                close=candle["close"],
                volume=candle["volume"],
            )
        )

    return history
