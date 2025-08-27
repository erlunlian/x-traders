"""
Tool registry for LangGraph agents to interact with the exchange.
These tools are structured for easy integration with LangChain/LangGraph.
"""

from typing import List
from uuid import UUID

from database import get_db_transaction
from database.repositories import XDataRepository
from enums import OrderType
from langchain_core.tools import StructuredTool
from models.responses import (
    AllXUsersResult,
    CancelResult,
    OrderResult,
    OrderStatusResult,
    PortfolioResult,
    RecentTweetsResult,
    TraderResult,
    TweetData,
    TweetsByIdsResult,
    UserTweetsResult,
    XUserData,
    XUserInfoResult,
)
from models.responses.market_data import (
    AllPricesResult,
    OrderBookData,
    OrderBookLevelData,
    PriceData,
    PriceResult,
    RecentTradesData,
    TickerListResult,
    TradeData,
)
from models.tools import (
    BuyOrderInput,
    CancelOrderInput,
    CreateTraderInput,
    GetAllXUsersInput,
    GetOrderBookInput,
    GetOrderStatusInput,
    GetPortfolioInput,
    GetPriceInput,
    GetRecentTradesInput,
    GetRecentTweetsInput,
    GetTweetsByIdsInput,
    GetUserTweetsInput,
    GetXUserInfoInput,
    SellOrderInput,
)
from services.market_data import (
    get_all_prices,
    get_available_tickers,
    get_current_price,
    get_order_book,
    get_recent_trades,
)
from services.trading import (
    cancel_order,
    create_trader,
    get_order_status,
    get_portfolio,
    place_buy_order,
    place_sell_order,
)


# Trading action tools
async def buy_stock(
    trader_id: str,
    ticker: str,
    quantity: int,
    order_type: str = "MARKET",
    limit_price_in_cents: int = None,
) -> OrderResult:
    """Place a buy order for stocks"""
    try:
        order_type_enum = OrderType[order_type]
        order_id = await place_buy_order(
            UUID(trader_id),
            ticker,
            quantity,
            order_type_enum,
            limit_price_in_cents,
        )
        return OrderResult(
            success=True,
            order_id=order_id,
            message=f"Buy order placed for {quantity} shares of {ticker}",
        )
    except Exception as e:
        return OrderResult(success=False, message="", error=str(e))


async def sell_stock(
    trader_id: str,
    ticker: str,
    quantity: int,
    order_type: str = "MARKET",
    limit_price_in_cents: int = None,
) -> OrderResult:
    """Place a sell order for stocks"""
    try:
        order_type_enum = OrderType[order_type]
        order_id = await place_sell_order(
            UUID(trader_id),
            ticker,
            quantity,
            order_type_enum,
            limit_price_in_cents,
        )
        return OrderResult(
            success=True,
            order_id=order_id,
            message=f"Sell order placed for {quantity} shares of {ticker}",
        )
    except Exception as e:
        return OrderResult(success=False, message="", error=str(e))


async def cancel_stock_order(trader_id: str, order_id: str) -> CancelResult:
    """Cancel an existing order"""
    try:
        success = await cancel_order(UUID(trader_id), UUID(order_id))
        if success:
            return CancelResult(
                success=True, message=f"Order {order_id} cancelled successfully"
            )
        else:
            return CancelResult(
                success=False,
                message="Order cannot be cancelled (already filled or expired)",
            )
    except Exception as e:
        return CancelResult(success=False, message="", error=str(e))


async def check_order_status(order_id: str) -> OrderStatusResult:
    """Check the status of an order"""
    try:
        status = await get_order_status(UUID(order_id))
        return OrderStatusResult(
            success=True,
            order_id=status.order_id,
            ticker=status.ticker,
            side=status.side.value,
            quantity=status.quantity,
            filled_quantity=status.filled_quantity,
            status=status.status.value,
            limit_price=status.limit_price,
        )
    except Exception as e:
        return OrderStatusResult(success=False, error=str(e))


async def check_portfolio(trader_id: str) -> PortfolioResult:
    """Check trader's portfolio"""
    try:
        portfolio = await get_portfolio(UUID(trader_id))
        return PortfolioResult(
            success=True,
            cash_balance_dollars=portfolio.cash_balance_in_cents / 100,
            positions=[
                {
                    "ticker": pos.ticker,
                    "quantity": pos.quantity,
                    "avg_cost_dollars": pos.avg_cost_in_cents / 100,
                }
                for pos in portfolio.positions
            ],
        )
    except Exception as e:
        return PortfolioResult(success=False, error=str(e))


async def create_new_trader(initial_cash_in_cents: int = 100_000_000) -> TraderResult:
    """Create a new trader account"""
    try:
        trader_id = await create_trader(initial_cash_in_cents)
        return TraderResult(
            success=True,
            trader_id=trader_id,
            initial_cash_dollars=initial_cash_in_cents / 100,
        )
    except Exception as e:
        return TraderResult(success=False, error=str(e))


# Market data tools
async def check_order_book(ticker: str) -> OrderBookData:
    """Get order book for a ticker showing all bid and ask levels"""
    try:
        result = await get_order_book(ticker)
        if result.success:
            return OrderBookData(
                success=True,
                ticker=result.ticker,
                bids=[
                    OrderBookLevelData(
                        price_dollars=level.price_in_cents / 100,
                        quantity=level.quantity,
                    )
                    for level in result.bids[:5]  # Top 5 levels
                ],
                asks=[
                    OrderBookLevelData(
                        price_dollars=level.price_in_cents / 100,
                        quantity=level.quantity,
                    )
                    for level in result.asks[:5]  # Top 5 levels
                ],
                last_price_dollars=(
                    result.last_price_in_cents / 100
                    if result.last_price_in_cents
                    else None
                ),
            )
        else:
            return OrderBookData(success=False, error=result.error)
    except Exception as e:
        return OrderBookData(success=False, error=str(e))


async def check_price(ticker: str) -> PriceResult:
    """Get current price and spread for a ticker"""
    try:
        price = await get_current_price(ticker)
        return PriceResult(
            success=True,
            ticker=price.ticker,
            last_price_dollars=(
                price.last_price_in_cents / 100 if price.last_price_in_cents else None
            ),
            best_bid_dollars=(
                price.best_bid_in_cents / 100 if price.best_bid_in_cents else None
            ),
            best_ask_dollars=(
                price.best_ask_in_cents / 100 if price.best_ask_in_cents else None
            ),
            bid_size=price.bid_size,
            ask_size=price.ask_size,
            spread_dollars=(
                price.spread_in_cents / 100 if price.spread_in_cents else None
            ),
        )
    except Exception as e:
        return PriceResult(success=False, error=str(e))


async def check_all_prices() -> AllPricesResult:
    """Get current prices for all tickers"""
    try:
        prices = await get_all_prices()
        price_data = [
            PriceData(
                ticker=p.ticker,
                last_price_dollars=(
                    p.last_price_in_cents / 100 if p.last_price_in_cents else None
                ),
                best_bid_dollars=(
                    p.best_bid_in_cents / 100 if p.best_bid_in_cents else None
                ),
                best_ask_dollars=(
                    p.best_ask_in_cents / 100 if p.best_ask_in_cents else None
                ),
                spread_dollars=(p.spread_in_cents / 100 if p.spread_in_cents else None),
            )
            for p in prices
        ]
        return AllPricesResult(success=True, prices=price_data)
    except Exception as e:
        return AllPricesResult(success=False, error=str(e))


async def check_recent_trades(ticker: str, limit: int = 20) -> RecentTradesData:
    """Get recent trades for a ticker"""
    try:
        result = await get_recent_trades(ticker, limit)
        if result.success:
            trade_data = [
                TradeData(
                    price_dollars=trade.price_in_cents / 100,
                    quantity=trade.quantity,
                    time=trade.executed_at.isoformat(),
                )
                for trade in result.trades
            ]
            return RecentTradesData(
                success=True, ticker=result.ticker, trades=trade_data
            )
        else:
            return RecentTradesData(success=False, error=result.error)
    except Exception as e:
        return RecentTradesData(success=False, error=str(e))


async def list_tickers() -> TickerListResult:
    """Get list of all tradeable tickers"""
    try:
        tickers = get_available_tickers()
        return TickerListResult(success=True, tickers=tickers)
    except Exception as e:
        return TickerListResult(success=False, error=str(e))


# X/Twitter data tools (read-only from database cache)
async def get_x_user_info(username: str) -> XUserInfoResult:
    """Get cached X/Twitter user information"""
    try:
        async with get_db_transaction() as session:
            repo = XDataRepository(session)
            user = await repo.get_user_or_none(username)

            if not user:
                return XUserInfoResult(
                    success=False, error=f"User @{username} not found in cache"
                )

            return XUserInfoResult(
                success=True,
                username=user.username,
                name=user.name,
                description=user.description,
                location=user.location,
                followers=user.num_followers,
                following=user.num_following,
                cached_at=user.fetched_at,
            )
    except Exception as e:
        return XUserInfoResult(success=False, error=str(e))


async def get_user_tweets(username: str, limit: int = 20) -> UserTweetsResult:
    """Get cached tweets from a specific user"""
    try:
        async with get_db_transaction() as session:
            repo = XDataRepository(session)
            tweets = await repo.get_tweets_by_username(username, limit)

            if not tweets:
                return UserTweetsResult(
                    success=False,
                    username=username,
                    error=f"No tweets found for @{username} in cache",
                )

            tweet_data = [
                TweetData(
                    tweet_id=tweet.tweet_id,
                    author=tweet.author_username,
                    text=tweet.text,
                    created_at=tweet.tweet_created_at,
                    likes=tweet.like_count,
                    retweets=tweet.retweet_count,
                    replies=tweet.reply_count,
                    quotes=tweet.quote_count,
                    views=tweet.view_count,
                    is_reply=tweet.is_reply,
                    cached_at=tweet.fetched_at,
                )
                for tweet in tweets
            ]

            return UserTweetsResult(
                success=True,
                username=username,
                tweet_count=len(tweet_data),
                tweets=tweet_data,
            )
    except Exception as e:
        return UserTweetsResult(success=False, error=str(e))


async def get_tweets_by_ids(tweet_ids: List[str]) -> TweetsByIdsResult:
    """Get specific cached tweets by their IDs"""
    if not tweet_ids:
        return TweetsByIdsResult(success=False, error="No tweet IDs provided")

    try:
        async with get_db_transaction() as session:
            repo = XDataRepository(session)
            tweets = await repo.get_tweets_by_ids(tweet_ids)

            found_ids = {tweet.tweet_id for tweet in tweets}
            missing_ids = [tid for tid in tweet_ids if tid not in found_ids]

            tweet_data = [
                TweetData(
                    tweet_id=tweet.tweet_id,
                    author=tweet.author_username,
                    text=tweet.text,
                    created_at=tweet.tweet_created_at,
                    likes=tweet.like_count,
                    retweets=tweet.retweet_count,
                    replies=tweet.reply_count,
                    quotes=tweet.quote_count,
                    views=tweet.view_count,
                    is_reply=tweet.is_reply,
                    cached_at=tweet.fetched_at,
                )
                for tweet in tweets
            ]

            return TweetsByIdsResult(
                success=True,
                requested=len(tweet_ids),
                found=len(tweets),
                missing_ids=missing_ids,
                tweets=tweet_data,
            )
    except Exception as e:
        return TweetsByIdsResult(success=False, error=str(e))


async def get_all_x_users() -> AllXUsersResult:
    """Get all cached X/Twitter users"""
    try:
        async with get_db_transaction() as session:
            repo = XDataRepository(session)
            users = await repo.get_all_users()

            user_data = [
                XUserData(
                    username=user.username,
                    name=user.name,
                    followers=user.num_followers,
                    following=user.num_following,
                    cached_at=user.fetched_at,
                )
                for user in users
            ]

            return AllXUsersResult(
                success=True, user_count=len(user_data), users=user_data
            )
    except Exception as e:
        return AllXUsersResult(success=False, error=str(e))


async def get_recent_tweets(limit: int = 50) -> RecentTweetsResult:
    """Get recent tweets from all cached users"""
    try:
        async with get_db_transaction() as session:
            repo = XDataRepository(session)
            tweets = await repo.get_all_tweets()

            # Apply limit
            tweets = tweets[:limit] if limit else tweets

            tweet_data = [
                TweetData(
                    tweet_id=tweet.tweet_id,
                    author=tweet.author_username,
                    text=tweet.text,
                    created_at=tweet.tweet_created_at,
                    likes=tweet.like_count,
                    retweets=tweet.retweet_count,
                    replies=tweet.reply_count,
                    quotes=tweet.quote_count,
                    views=tweet.view_count,
                    is_reply=tweet.is_reply,
                    cached_at=tweet.fetched_at,
                )
                for tweet in tweets
            ]

            return RecentTweetsResult(
                success=True, tweet_count=len(tweet_data), tweets=tweet_data
            )
    except Exception as e:
        return RecentTweetsResult(success=False, error=str(e))


# Agent utility tools
async def rest(duration_minutes: int = 5) -> dict:
    """Take a break for a specified duration"""
    import asyncio

    await asyncio.sleep(duration_minutes * 60)
    return {"success": True, "rested": True, "duration_minutes": duration_minutes}


def get_trading_tools() -> List[StructuredTool]:
    """
    Get all trading tools for LangGraph agents.

    Returns:
        List of StructuredTool objects ready for use in LangGraph
    """
    return [
        # Trading actions
        StructuredTool.from_function(
            func=buy_stock,
            name="buy_stock",
            description="Place a buy order for stocks",
            args_schema=BuyOrderInput,
            coroutine=buy_stock,
        ),
        StructuredTool.from_function(
            func=sell_stock,
            name="sell_stock",
            description="Place a sell order for stocks",
            args_schema=SellOrderInput,
            coroutine=sell_stock,
        ),
        StructuredTool.from_function(
            func=cancel_stock_order,
            name="cancel_order",
            description="Cancel an existing order",
            args_schema=CancelOrderInput,
            coroutine=cancel_stock_order,
        ),
        StructuredTool.from_function(
            func=check_order_status,
            name="check_order_status",
            description="Check the status of an order",
            args_schema=GetOrderStatusInput,
            coroutine=check_order_status,
        ),
        StructuredTool.from_function(
            func=check_portfolio,
            name="check_portfolio",
            description="Check trader's portfolio and cash balance",
            args_schema=GetPortfolioInput,
            coroutine=check_portfolio,
        ),
        StructuredTool.from_function(
            func=create_new_trader,
            name="create_trader",
            description="Create a new trader account with initial cash",
            args_schema=CreateTraderInput,
            coroutine=create_new_trader,
        ),
        # Market data
        StructuredTool.from_function(
            func=check_order_book,
            name="check_order_book",
            description="Get order book showing bid/ask levels for a ticker",
            args_schema=GetOrderBookInput,
            coroutine=check_order_book,
        ),
        StructuredTool.from_function(
            func=check_price,
            name="check_price",
            description="Get current price and spread for a ticker",
            args_schema=GetPriceInput,
            coroutine=check_price,
        ),
        StructuredTool.from_function(
            func=check_all_prices,
            name="check_all_prices",
            description="Get current prices for all tradeable tickers",
            coroutine=check_all_prices,
        ),
        StructuredTool.from_function(
            func=check_recent_trades,
            name="check_recent_trades",
            description="Get recent trades for a ticker",
            args_schema=GetRecentTradesInput,
            coroutine=check_recent_trades,
        ),
        StructuredTool.from_function(
            func=list_tickers,
            name="list_tickers",
            description="Get list of all tradeable ticker symbols",
            coroutine=list_tickers,
        ),
    ]


def get_x_data_tools() -> List[StructuredTool]:
    """
    Get all X/Twitter data tools for LangGraph agents.

    Returns:
        List of StructuredTool objects for X/Twitter data access
    """
    return [
        StructuredTool.from_function(
            func=get_x_user_info,
            name="get_x_user_info",
            description="Get cached X/Twitter user profile information",
            args_schema=GetXUserInfoInput,
            coroutine=get_x_user_info,
        ),
        StructuredTool.from_function(
            func=get_user_tweets,
            name="get_user_tweets",
            description="Get cached tweets from a specific user",
            args_schema=GetUserTweetsInput,
            coroutine=get_user_tweets,
        ),
        StructuredTool.from_function(
            func=get_tweets_by_ids,
            name="get_tweets_by_ids",
            description="Get specific cached tweets by their IDs",
            args_schema=GetTweetsByIdsInput,
            coroutine=get_tweets_by_ids,
        ),
        StructuredTool.from_function(
            func=get_all_x_users,
            name="get_all_x_users",
            description="Get all cached X/Twitter users",
            args_schema=GetAllXUsersInput,
            coroutine=get_all_x_users,
        ),
        StructuredTool.from_function(
            func=get_recent_tweets,
            name="get_recent_tweets",
            description="Get recent tweets from all cached users",
            args_schema=GetRecentTweetsInput,
            coroutine=get_recent_tweets,
        ),
    ]


def get_utility_tools() -> List[StructuredTool]:
    return [
        StructuredTool(
            func=rest,
            name="rest",
            description="Take a break for a specified duration in minutes",
            coroutine=rest,
        )
    ]
