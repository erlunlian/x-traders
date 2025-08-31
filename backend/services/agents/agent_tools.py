"""
Tool registry for LangGraph agents to interact with the exchange.
These tools are structured for easy integration with LangChain/LangGraph.
"""

import asyncio
from typing import List
from uuid import UUID

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from database import get_db_transaction
from database.repositories import XDataRepository
from database.repositories_social import SocialRepository
from enums import AgentToolName, OrderType
from models.responses import (
    AllXUsersResult,
    CancelResult,
    OrderResult,
    OrderStatusResult,
    PortfolioResult,
    RecentTweetsResult,
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
from models.responses.social import PostSummary, RecentCommentsResult, RecentPostsResult

# Tool input schemas are now defined in this file using Pydantic models with Field descriptions
from services.market_data import (
    get_all_prices,
    get_available_tickers,
    get_current_price,
    get_order_book,
    get_recent_trades,
)
from services.trading import (
    cancel_order,
    get_order_status,
    get_portfolio,
    place_buy_order,
    place_sell_order,
)


# Pydantic models for tool inputs with descriptions
class BuyLimitOrderInput(BaseModel):
    """Input for placing a limit buy order"""

    ticker: str = Field(description="Stock ticker symbol (e.g., '@elonmusk', '@sama')")
    quantity: int = Field(description="Number of shares to buy", gt=0)
    limit_price_in_cents: int = Field(
        description="Maximum price per share in cents (e.g., 10050 for $100.50)", gt=0
    )
    tif_seconds: int = Field(
        default=60,
        description="Time in force - how long the order stays active in seconds",
        ge=1,
        le=86400,
    )


class BuyLimitOrderInputWithTraderId(BuyLimitOrderInput):
    """Input for placing a limit buy order with trader_id"""

    trader_id: str = Field(description="The unique identifier of the trader")


class SellLimitOrderInput(BaseModel):
    """Input for placing a limit sell order"""

    ticker: str = Field(description="Stock ticker symbol (e.g., '@elonmusk', '@sama')")
    quantity: int = Field(description="Number of shares to sell", gt=0)
    limit_price_in_cents: int = Field(
        description="Minimum price per share in cents (e.g., 10050 for $100.50)", gt=0
    )
    tif_seconds: int = Field(
        default=60,
        description="Time in force - how long the order stays active in seconds",
        ge=1,
        le=86400,
    )


class SellLimitOrderInputWithTraderId(SellLimitOrderInput):
    """Input for placing a limit sell order with trader_id"""

    trader_id: str = Field(description="The unique identifier of the trader")


class CancelOrderInput(BaseModel):
    """Input for canceling an order"""

    order_id: str = Field(description="The unique identifier of the order to cancel")


class CancelOrderInputWithTraderId(CancelOrderInput):
    """Input for canceling an order with trader_id"""

    trader_id: str = Field(description="The unique identifier of the trader")


# Market data input schemas
class OrderStatusInput(BaseModel):
    """Input for checking order status"""

    order_id: str = Field(description="The unique identifier of the order to check")


class OrderBookInput(BaseModel):
    """Input for getting order book data"""

    ticker: str = Field(description="Stock ticker symbol (e.g., '@elonmusk', '@sama')")


class PriceInput(BaseModel):
    """Input for checking current price"""

    ticker: str = Field(description="Stock ticker symbol (e.g., '@elonmusk', '@sama')")


class RecentTradesInput(BaseModel):
    """Input for getting recent trades"""

    ticker: str = Field(description="Stock ticker symbol (e.g., '@elonmusk', '@sama')")
    limit: int = Field(default=10, description="Maximum number of trades to return", ge=1, le=100)


# X/Twitter data input schemas
class XUserInfoInput(BaseModel):
    """Input for getting X/Twitter user information"""

    username: str = Field(description="X/Twitter username without @ (e.g., 'elonmusk', 'sama')")


class UserTweetsInput(BaseModel):
    """Input for getting tweets from a specific user"""

    username: str = Field(description="X/Twitter username without @ (e.g., 'elonmusk', 'sama')")
    limit: int = Field(default=10, description="Maximum number of tweets to return", ge=1, le=100)


class RecentTweetsInput(BaseModel):
    """Input for getting recent tweets from all cached users"""

    limit: int = Field(default=20, description="Maximum number of tweets to return", ge=1, le=100)


class TweetsByIdsInput(BaseModel):
    """Input for getting specific tweets by their IDs"""

    tweet_ids: list[str] = Field(description="List of tweet IDs to retrieve")


# Utility input schemas
class RestInput(BaseModel):
    """Input for taking a rest/break"""

    duration_minutes: int = Field(description="Duration to rest in minutes", ge=1, le=300)


# Social feed input schemas
class CreatePostInput(BaseModel):
    ticker: str = Field(description="Ticker symbol (e.g., '@elonmusk')")
    content: str = Field(description="Post content")


class CreatePostInputWithTraderId(CreatePostInput):
    trader_id: str = Field(description="The unique identifier of the trader")


class LikePostInput(BaseModel):
    post_id: str = Field(description="Post UUID to like")


class LikePostInputWithTraderId(LikePostInput):
    trader_id: str = Field(description="The unique identifier of the trader")


class AddCommentInput(BaseModel):
    post_id: str = Field(description="Post UUID to comment on")
    content: str = Field(description="Comment content")


class AddCommentInputWithTraderId(AddCommentInput):
    trader_id: str = Field(description="The unique identifier of the trader")


class RecentTickerPostsInput(BaseModel):
    ticker: str = Field(description="Ticker symbol")
    limit: int = Field(default=20, ge=1, le=100)


class RecentPostCommentsInput(BaseModel):
    post_id: str = Field(description="Post UUID")
    limit: int = Field(default=20, ge=1, le=100)


# Social feed tools
async def create_post(**kwargs) -> dict:
    input_data = CreatePostInputWithTraderId(**kwargs)
    from uuid import UUID

    async with get_db_transaction() as session:
        repo = SocialRepository(session)
        post = await repo.create_post(agent_id=UUID(input_data.trader_id), ticker=input_data.ticker, content=input_data.content)  # type: ignore[name-defined]
        return {"success": True, "post_id": str(post.post_id)}


async def like_post(**kwargs) -> dict:
    input_data = LikePostInputWithTraderId(**kwargs)
    from uuid import UUID

    async with get_db_transaction() as session:
        repo = SocialRepository(session)
        await repo.like_post(
            agent_id=UUID(input_data.trader_id),
            post_id=UUID(input_data.post_id),
        )
        return {"success": True}


async def add_comment(**kwargs) -> dict:
    input_data = AddCommentInputWithTraderId(**kwargs)
    from uuid import UUID

    async with get_db_transaction() as session:
        repo = SocialRepository(session)
        comment = await repo.add_comment(
            agent_id=UUID(input_data.trader_id),
            post_id=UUID(input_data.post_id),
            content=input_data.content,
        )
        return {"success": True, "comment_id": str(comment.comment_id)}


async def get_recent_ticker_posts(**kwargs) -> RecentPostsResult:
    input_data = RecentTickerPostsInput(**kwargs)
    async with get_db_transaction() as session:
        repo = SocialRepository(session)
        posts = await repo.get_recent_posts_by_ticker(input_data.ticker, input_data.limit)
        post_ids = [p.post_id for p in posts]
        stats = await repo.get_post_counts(post_ids)
        counts = {s.post_id: (s.like_count, s.comment_count) for s in stats}

        summaries = [
            PostSummary(
                post_id=p.post_id,
                ticker=p.ticker,
                agent_id=p.agent_id,
                content=p.content,
                created_at=p.created_at,
                likes=counts.get(p.post_id, (0, 0))[0],
                comments=counts.get(p.post_id, (0, 0))[1],
            )
            for p in posts
        ]
        return RecentPostsResult(success=True, ticker=input_data.ticker, posts=summaries)


async def get_recent_post_comments(**kwargs) -> RecentCommentsResult:
    input_data = RecentPostCommentsInput(**kwargs)
    from uuid import UUID

    async with get_db_transaction() as session:
        repo = SocialRepository(session)
        comments = await repo.get_recent_comments(UUID(input_data.post_id), input_data.limit)
        from models.responses.social import CommentData

        items = [
            CommentData(
                comment_id=c.comment_id,
                post_id=c.post_id,
                agent_id=c.agent_id,
                content=c.content,
                created_at=c.created_at,
            )
            for c in comments
        ]
        return RecentCommentsResult(success=True, post_id=UUID(input_data.post_id), comments=items)


# Trading action tools
async def buy_stock(**kwargs) -> OrderResult:
    """Place a LIMIT buy order for stocks"""
    input_data = BuyLimitOrderInputWithTraderId(**kwargs)
    try:
        order_id = await place_buy_order(
            UUID(input_data.trader_id),
            input_data.ticker,
            input_data.quantity,
            OrderType.LIMIT,
            input_data.limit_price_in_cents,
            input_data.tif_seconds,
        )
        return OrderResult(
            success=True,
            order_id=order_id,
            message=f"Buy order placed for {input_data.quantity} shares of {input_data.ticker}",
        )
    except Exception as e:
        return OrderResult(success=False, message="", error=str(e))


async def sell_stock(**kwargs) -> OrderResult:
    """Place a LIMIT sell order for stocks"""
    input_data = SellLimitOrderInputWithTraderId(**kwargs)
    try:
        order_id = await place_sell_order(
            UUID(input_data.trader_id),
            input_data.ticker,
            input_data.quantity,
            OrderType.LIMIT,
            input_data.limit_price_in_cents,
            input_data.tif_seconds,
        )
        return OrderResult(
            success=True,
            order_id=order_id,
            message=f"Sell order placed for {input_data.quantity} shares of {input_data.ticker}",
        )
    except Exception as e:
        return OrderResult(success=False, message="", error=str(e))


async def cancel_stock_order(**kwargs) -> CancelResult:
    """Cancel an existing order"""
    input_data = CancelOrderInputWithTraderId(**kwargs)
    try:
        success = await cancel_order(UUID(input_data.trader_id), UUID(input_data.order_id))
        if success:
            return CancelResult(
                success=True, message=f"Order {input_data.order_id} cancelled successfully"
            )
        else:
            return CancelResult(
                success=False,
                message="Order cannot be cancelled (already filled or expired)",
            )
    except Exception as e:
        return CancelResult(success=False, message="", error=str(e))


async def check_order_status(**kwargs) -> OrderStatusResult:
    """Check the status of an order"""
    input_data = OrderStatusInput(**kwargs)
    try:
        status = await get_order_status(UUID(input_data.order_id))
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


# Market data tools
async def check_order_book(**kwargs) -> OrderBookData:
    """Get order book for a ticker showing all bid and ask levels"""
    input_data = OrderBookInput(**kwargs)
    try:
        result = await get_order_book(input_data.ticker)
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
                    result.last_price_in_cents / 100 if result.last_price_in_cents else None
                ),
                current_price_dollars=(
                    result.current_price_in_cents / 100 if result.current_price_in_cents else None
                ),
            )
        else:
            return OrderBookData(success=False, error=result.error)
    except Exception as e:
        return OrderBookData(success=False, error=str(e))


async def check_price(**kwargs) -> PriceResult:
    """Get current price and spread for a ticker"""
    input_data = PriceInput(**kwargs)
    try:
        price = await get_current_price(input_data.ticker)
        return PriceResult(
            success=True,
            ticker=price.ticker,
            last_price_dollars=(
                price.last_price_in_cents / 100 if price.last_price_in_cents else None
            ),
            best_bid_dollars=(price.best_bid_in_cents / 100 if price.best_bid_in_cents else None),
            best_ask_dollars=(price.best_ask_in_cents / 100 if price.best_ask_in_cents else None),
            bid_size=price.bid_size,
            ask_size=price.ask_size,
            spread_dollars=(price.spread_in_cents / 100 if price.spread_in_cents else None),
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
                last_price_dollars=(p.last_price_in_cents / 100 if p.last_price_in_cents else None),
                best_bid_dollars=(p.best_bid_in_cents / 100 if p.best_bid_in_cents else None),
                best_ask_dollars=(p.best_ask_in_cents / 100 if p.best_ask_in_cents else None),
                spread_dollars=(p.spread_in_cents / 100 if p.spread_in_cents else None),
            )
            for p in prices
        ]
        return AllPricesResult(success=True, prices=price_data)
    except Exception as e:
        return AllPricesResult(success=False, error=str(e))


async def check_recent_trades(**kwargs) -> RecentTradesData:
    """Get recent trades for a ticker"""
    input_data = RecentTradesInput(**kwargs)
    try:
        result = await get_recent_trades(input_data.ticker, input_data.limit)
        if result.success:
            trade_data = [
                TradeData(
                    price_dollars=trade.price_in_cents / 100,
                    quantity=trade.quantity,
                    time=trade.executed_at.isoformat(),
                )
                for trade in result.trades
            ]
            return RecentTradesData(success=True, ticker=result.ticker, trades=trade_data)
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
async def get_x_user_info(**kwargs) -> XUserInfoResult:
    """Get cached X/Twitter user information"""
    input_data = XUserInfoInput(**kwargs)
    try:
        async with get_db_transaction() as session:
            repo = XDataRepository(session)
            user = await repo.get_user_or_none(input_data.username)

            if not user:
                return XUserInfoResult(
                    success=False, error=f"User @{input_data.username} not found in cache"
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


async def get_user_tweets(**kwargs) -> UserTweetsResult:
    """Get cached tweets from a specific user"""
    input_data = UserTweetsInput(**kwargs)
    try:
        async with get_db_transaction() as session:
            repo = XDataRepository(session)
            tweets = await repo.get_tweets_by_username(input_data.username, input_data.limit)

            if not tweets:
                return UserTweetsResult(
                    success=False,
                    username=input_data.username,
                    error=f"No tweets found for @{input_data.username} in cache",
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
                username=input_data.username,
                tweet_count=len(tweet_data),
                tweets=tweet_data,
            )
    except Exception as e:
        return UserTweetsResult(success=False, error=str(e))


async def get_tweets_by_ids(**kwargs) -> TweetsByIdsResult:
    """Get specific cached tweets by their IDs"""
    input_data = TweetsByIdsInput(**kwargs)
    if not input_data.tweet_ids:
        return TweetsByIdsResult(success=False, error="No tweet IDs provided")

    try:
        async with get_db_transaction() as session:
            repo = XDataRepository(session)
            tweets = await repo.get_tweets_by_ids(input_data.tweet_ids)

            found_ids = {tweet.tweet_id for tweet in tweets}
            missing_ids = [tid for tid in input_data.tweet_ids if tid not in found_ids]

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
                requested=len(input_data.tweet_ids),
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

            return AllXUsersResult(success=True, user_count=len(user_data), users=user_data)
    except Exception as e:
        return AllXUsersResult(success=False, error=str(e))


async def get_x_recent_tweets(**kwargs) -> RecentTweetsResult:
    """Get recent tweets from all cached users"""
    input_data = RecentTweetsInput(**kwargs)
    try:
        async with get_db_transaction() as session:
            repo = XDataRepository(session)
            tweets = await repo.get_all_tweets()

            # Apply limit
            tweets = tweets[: input_data.limit] if input_data.limit else tweets

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

            return RecentTweetsResult(success=True, tweet_count=len(tweet_data), tweets=tweet_data)
    except Exception as e:
        return RecentTweetsResult(success=False, error=str(e))


# Agent utility tools
async def rest(**kwargs) -> dict:
    """Take a break for a specified duration"""
    input_data = RestInput(**kwargs)
    await asyncio.sleep(input_data.duration_minutes * 60)
    return {"success": True, "rested": True, "duration_minutes": input_data.duration_minutes}


def get_social_tools(trader_id: str) -> List[StructuredTool]:
    """
    Get all social tools for LangGraph agents.
    """

    async def create_post_with_embedded_trader_id(**kwargs) -> dict:
        return await create_post(trader_id=trader_id, **kwargs)

    async def like_post_with_embedded_trader_id(**kwargs) -> dict:
        return await like_post(trader_id=trader_id, **kwargs)

    async def add_comment_with_embedded_trader_id(**kwargs) -> dict:
        return await add_comment(trader_id=trader_id, **kwargs)

    return [
        StructuredTool.from_function(
            func=create_post_with_embedded_trader_id,
            name=AgentToolName.CREATE_POST,
            description="Create a social post under a ticker to share your opinion or research, to sway public sentiment, or to influence price.",
            args_schema=CreatePostInput,
            coroutine=create_post,
        ),
        StructuredTool.from_function(
            func=like_post_with_embedded_trader_id,
            name=AgentToolName.LIKE_POST,
            description="Like a social post to show your support or agreement.",
            args_schema=LikePostInput,
            coroutine=like_post_with_embedded_trader_id,
        ),
        StructuredTool.from_function(
            func=add_comment_with_embedded_trader_id,
            name=AgentToolName.ADD_COMMENT,
            description="Add a comment to a social post to share your opinion or research.",
            args_schema=AddCommentInput,
            coroutine=add_comment_with_embedded_trader_id,
        ),
        StructuredTool.from_function(
            func=get_recent_ticker_posts,
            name=AgentToolName.GET_TICKER_POSTS,
            description="Get recent social posts for a ticker to see what people are saying about it.",
            args_schema=RecentTickerPostsInput,
            coroutine=get_recent_ticker_posts,
        ),
        StructuredTool.from_function(
            func=get_recent_post_comments,
            name=AgentToolName.GET_POST_COMMENTS,
            description="Get recent comments for a post to see what people are saying about it.",
            args_schema=RecentPostCommentsInput,
            coroutine=get_recent_post_comments,
        ),
    ]


def get_trading_tools(trader_id: str) -> List[StructuredTool]:
    """
    Get all trading tools for LangGraph agents.

    Args:
        trader_id: The trader_id to bind to all trading tools (required)

    Returns:
        List of StructuredTool objects ready for use in LangGraph
    """

    # Create wrapper functions that include the trader_id
    async def buy_limit_with_embedded_trader_id(**kwargs) -> OrderResult:
        return await buy_stock(trader_id=trader_id, **kwargs)

    async def sell_limit_with_embedded_trader_id(**kwargs) -> OrderResult:
        return await sell_stock(trader_id=trader_id, **kwargs)

    async def cancel_stock_order_with_embedded_trader_id(**kwargs) -> CancelResult:
        return await cancel_stock_order(trader_id=trader_id, **kwargs)

    async def check_portfolio_wrapped_with_embedded_trader_id() -> PortfolioResult:
        return await check_portfolio(trader_id)

    return [
        # Trading actions with trader_id bound
        StructuredTool.from_function(
            func=buy_limit_with_embedded_trader_id,
            name=AgentToolName.BUY_LIMIT,
            description="Place a LIMIT buy order that executes at or below the specified price",
            args_schema=BuyLimitOrderInput,
            coroutine=buy_limit_with_embedded_trader_id,
        ),
        StructuredTool.from_function(
            func=sell_limit_with_embedded_trader_id,
            name=AgentToolName.SELL_LIMIT,
            description="Place a LIMIT sell order that executes at or above the specified price",
            args_schema=SellLimitOrderInput,
            coroutine=sell_limit_with_embedded_trader_id,
        ),
        StructuredTool.from_function(
            func=cancel_stock_order_with_embedded_trader_id,
            name=AgentToolName.CANCEL_ORDER,
            description="Cancel an existing order",
            args_schema=CancelOrderInput,
            coroutine=cancel_stock_order_with_embedded_trader_id,
        ),
        StructuredTool.from_function(
            func=check_order_status,
            name=AgentToolName.CHECK_ORDER_STATUS,
            description="Check the status of an order",
            args_schema=OrderStatusInput,
            coroutine=check_order_status,
        ),
        StructuredTool.from_function(
            func=check_portfolio_wrapped_with_embedded_trader_id,
            name=AgentToolName.CHECK_PORTFOLIO,
            description="Check your current portfolio and cash balance",
            coroutine=check_portfolio_wrapped_with_embedded_trader_id,
        ),
        # Market data tools
        StructuredTool.from_function(
            func=check_order_book,
            name=AgentToolName.CHECK_ORDER_BOOK,
            description="Get order book showing bid/ask levels for a ticker",
            args_schema=OrderBookInput,
            coroutine=check_order_book,
        ),
        StructuredTool.from_function(
            func=check_price,
            name=AgentToolName.CHECK_PRICE,
            description="Get current price and spread for a ticker",
            args_schema=PriceInput,
            coroutine=check_price,
        ),
        StructuredTool.from_function(
            func=check_all_prices,
            name=AgentToolName.CHECK_ALL_PRICES,
            description="Get current prices for all tradeable tickers",
            coroutine=check_all_prices,
        ),
        StructuredTool.from_function(
            func=check_recent_trades,
            name=AgentToolName.CHECK_RECENT_TRADES,
            description="Get recent trades for a ticker",
            args_schema=RecentTradesInput,
            coroutine=check_recent_trades,
        ),
        StructuredTool.from_function(
            func=list_tickers,
            name=AgentToolName.LIST_TICKERS,
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
            name=AgentToolName.GET_X_USER_INFO,
            description="Get cached X/Twitter user profile information",
            args_schema=XUserInfoInput,
            coroutine=get_x_user_info,
        ),
        StructuredTool.from_function(
            func=get_user_tweets,
            name=AgentToolName.GET_X_USER_TWEETS,
            description="Get cached tweets from a specific user",
            args_schema=UserTweetsInput,
            coroutine=get_user_tweets,
        ),
        StructuredTool.from_function(
            func=get_tweets_by_ids,
            name=AgentToolName.GET_X_TWEETS_BY_IDS,
            description="Get specific cached tweets by their IDs",
            args_schema=TweetsByIdsInput,
            coroutine=get_tweets_by_ids,
        ),
        StructuredTool.from_function(
            func=get_all_x_users,
            name=AgentToolName.GET_ALL_X_USERS,
            description="Get all cached X/Twitter users",
            coroutine=get_all_x_users,
        ),
        StructuredTool.from_function(
            func=get_x_recent_tweets,
            name=AgentToolName.GET_X_RECENT_TWEETS,
            description="Get recent tweets from all cached users",
            args_schema=RecentTweetsInput,
            coroutine=get_x_recent_tweets,
        ),
    ]


def get_utility_tools() -> List[StructuredTool]:
    return [
        StructuredTool.from_function(
            func=rest,
            name=AgentToolName.REST,
            description="Take a break for a specified duration in minutes",
            args_schema=RestInput,
            coroutine=rest,
        )
    ]
