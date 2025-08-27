"""
Market data service for AI agents to query exchange information
"""

from typing import List

from database import async_session
from database.repositories import TradeRepository
from engine import order_router
from models.core import Ticker
from models.responses import (
    OrderBookLevel,
    OrderBookResult,
    PriceInfo,
    RecentTradesResult,
    TradeInfo,
)


async def get_order_book(ticker: str) -> OrderBookResult:
    """
    Get current order book for a ticker.

    Args:
        ticker: Symbol to query (e.g., "@elonmusk")

    Returns:
        OrderBookResult with bid/ask levels
    """
    try:
        Ticker.validate_or_raise(ticker)

        snapshot = order_router.get_order_book(ticker)

        # Convert to sorted lists of levels
        bids = [
            OrderBookLevel(price_in_cents=price, quantity=qty)
            for price, qty in sorted(snapshot.bids.items(), reverse=True)
        ]
        asks = [
            OrderBookLevel(price_in_cents=price, quantity=qty)
            for price, qty in sorted(snapshot.asks.items())
        ]

        return OrderBookResult(
            success=True,
            ticker=ticker,
            bids=bids,
            asks=asks,
            last_price_in_cents=snapshot.last_price_in_cents,
        )
    except Exception as e:
        return OrderBookResult(success=False, error=str(e))


async def get_current_price(ticker: str) -> PriceInfo:
    """
    Get current price and best bid/ask for a ticker.

    Args:
        ticker: Symbol to query (e.g., "@elonmusk")

    Returns:
        PriceInfo with current market prices
    """
    Ticker.validate_or_raise(ticker)

    snapshot = order_router.get_order_book(ticker)

    best_bid_in_cents = max(snapshot.bids.keys()) if snapshot.bids else None
    best_ask_in_cents = min(snapshot.asks.keys()) if snapshot.asks else None

    spread_in_cents = None
    if best_bid_in_cents and best_ask_in_cents:
        spread_in_cents = best_ask_in_cents - best_bid_in_cents

    bid_size = snapshot.bids.get(best_bid_in_cents, 0) if best_bid_in_cents else None
    ask_size = snapshot.asks.get(best_ask_in_cents, 0) if best_ask_in_cents else None

    return PriceInfo(
        ticker=ticker,
        last_price_in_cents=snapshot.last_price_in_cents,
        best_bid_in_cents=best_bid_in_cents,
        best_ask_in_cents=best_ask_in_cents,
        bid_size=bid_size,
        ask_size=ask_size,
        spread_in_cents=spread_in_cents,
    )


async def get_all_prices() -> List[PriceInfo]:
    """
    Get current prices for all tickers.

    Returns:
        List of PriceInfo for all tradeable tickers
    """
    prices = []
    for ticker in Ticker.get_all():
        try:
            price_info = await get_current_price(ticker)
            prices.append(price_info)
        except Exception:
            # Include ticker even if no data
            prices.append(
                PriceInfo(
                    ticker=ticker,
                    last_price_in_cents=None,
                    best_bid_in_cents=None,
                    best_ask_in_cents=None,
                    bid_size=None,
                    ask_size=None,
                    spread_in_cents=None,
                )
            )
    return prices


async def get_recent_trades(ticker: str, limit: int = 20) -> RecentTradesResult:
    """
    Get recent trades for a ticker.

    Args:
        ticker: Symbol to query (e.g., "@elonmusk")
        limit: Number of trades to return (max 100)

    Returns:
        RecentTradesResult with recent trades
    """
    try:
        Ticker.validate_or_raise(ticker)

        limit = min(limit, 100)  # Cap at 100

        async with async_session() as session:
            trade_repo = TradeRepository(session)
            trades = await trade_repo.get_recent_trades(ticker, limit)

            trade_list = [
                TradeInfo(
                    trade_id=trade.trade_id,
                    ticker=trade.ticker,
                    price_in_cents=trade.price,
                    quantity=trade.quantity,
                    executed_at=trade.executed_at,
                )
                for trade in trades
            ]

            return RecentTradesResult(
                success=True,
                ticker=ticker,
                trades=trade_list,
            )
    except Exception as e:
        return RecentTradesResult(success=False, error=str(e))


def get_available_tickers() -> List[str]:
    """
    Get list of all tradeable tickers.

    Returns:
        List of ticker symbols
    """
    return Ticker.get_all()
