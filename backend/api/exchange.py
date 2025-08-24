"""
Exchange API endpoints for market data (read-only)
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from database import async_session
from database.repositories import TradeRepository
from engine import order_router
from fastapi import APIRouter, HTTPException, Query
from models.schemas import OrderBookSnapshot
from pydantic import BaseModel

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
    last_price_in_cents: Optional[int]
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
        last_price_in_cents=snapshot.last_price_in_cents,
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
                last_price_in_cents=snapshot.last_price_in_cents,
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
    For now, returns mock data - will be implemented with real trade aggregation.
    """
    if ticker not in order_router.get_tickers():
        raise HTTPException(status_code=404, detail=f"Ticker not found: {ticker}")

    # Time range to number of points mapping
    range_config = {
        "1d": 24,  # 24 hourly points
        "1w": 28,  # 4 points per day for a week
        "1m": 30,  # Daily points for a month
        "6m": 26,  # Weekly points for 6 months
        "1y": 52,  # Weekly points for a year
    }

    # Get num_points with a default value of 24
    num_points = range_config.get(time_range, 24)

    # Generate mock OHLC data
    # In production, this would aggregate actual trade data
    import random
    from datetime import timedelta

    now = datetime.now()
    base_price = 10000  # $100 in cents
    history = []

    for i in range(num_points):
        # Calculate how far back this point should be
        periods_ago = num_points - i - 1
        if time_range == "1d":
            timestamp = now - timedelta(hours=periods_ago)
        else:
            timestamp = now - timedelta(days=periods_ago)

        # Generate OHLC values with some randomness
        open_price = base_price + random.randint(-500, 500)
        close_price = base_price + random.randint(-500, 500)
        high_price = max(open_price, close_price) + random.randint(0, 200)
        low_price = min(open_price, close_price) - random.randint(0, 200)
        volume = random.randint(100, 10000)

        history.append(
            PriceHistoryPoint(
                timestamp=timestamp,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
            )
        )

        # Update base price for next iteration
        base_price = close_price

    return history
