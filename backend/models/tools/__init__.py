"""
Input/output models for agent tools
"""
from pydantic import BaseModel, Field


class BuyOrderInput(BaseModel):
    """Input for placing a buy order"""
    trader_id: str = Field(description="UUID of the trader")
    ticker: str = Field(description="Ticker symbol (e.g., '@elonmusk')")
    quantity: int = Field(description="Number of shares to buy", gt=0)
    order_type: str = Field(
        default="MARKET",
        description="Order type: MARKET, LIMIT, or IOC"
    )
    limit_price_in_cents: int = Field(
        default=None,
        description="Maximum price in cents (required for LIMIT orders)"
    )


class SellOrderInput(BaseModel):
    """Input for placing a sell order"""
    trader_id: str = Field(description="UUID of the trader")
    ticker: str = Field(description="Ticker symbol (e.g., '@elonmusk')")
    quantity: int = Field(description="Number of shares to sell", gt=0)
    order_type: str = Field(
        default="MARKET",
        description="Order type: MARKET, LIMIT, or IOC"
    )
    limit_price_in_cents: int = Field(
        default=None,
        description="Minimum price in cents (required for LIMIT orders)"
    )


class CancelOrderInput(BaseModel):
    """Input for canceling an order"""
    trader_id: str = Field(description="UUID of the trader")
    order_id: str = Field(description="UUID of the order to cancel")


class GetOrderStatusInput(BaseModel):
    """Input for getting order status"""
    order_id: str = Field(description="UUID of the order")


class GetPortfolioInput(BaseModel):
    """Input for getting portfolio"""
    trader_id: str = Field(description="UUID of the trader")


class CreateTraderInput(BaseModel):
    """Input for creating a new trader"""
    initial_cash_in_cents: int = Field(
        default=100_000_000,
        description="Initial cash balance in cents (default $1,000,000)"
    )


class GetOrderBookInput(BaseModel):
    """Input for getting order book"""
    ticker: str = Field(description="Ticker symbol (e.g., '@elonmusk')")


class GetPriceInput(BaseModel):
    """Input for getting current price"""
    ticker: str = Field(description="Ticker symbol (e.g., '@elonmusk')")


class GetRecentTradesInput(BaseModel):
    """Input for getting recent trades"""
    ticker: str = Field(description="Ticker symbol (e.g., '@elonmusk')")
    limit: int = Field(default=20, description="Number of trades to return (max 100)")


# X/Twitter data tool inputs
class GetXUserInfoInput(BaseModel):
    """Input for getting X/Twitter user information"""
    username: str = Field(description="Twitter username (without @)")


class GetUserTweetsInput(BaseModel):
    """Input for getting tweets from a user"""
    username: str = Field(description="Twitter username (without @)")
    limit: int = Field(default=20, description="Number of tweets to return (max 100)")


class GetTweetsByIdsInput(BaseModel):
    """Input for getting specific tweets by IDs"""
    tweet_ids: list[str] = Field(description="List of tweet IDs to fetch")


class GetAllXUsersInput(BaseModel):
    """Input for getting all cached X/Twitter users"""
    pass  # No parameters needed


class GetRecentTweetsInput(BaseModel):
    """Input for getting recent tweets from all cached users"""
    limit: int = Field(default=50, description="Number of tweets to return (max 200)")


__all__ = [
    "BuyOrderInput",
    "SellOrderInput",
    "CancelOrderInput",
    "GetOrderStatusInput",
    "GetPortfolioInput",
    "CreateTraderInput",
    "GetOrderBookInput",
    "GetPriceInput",
    "GetRecentTradesInput",
    # X/Twitter data tools
    "GetXUserInfoInput",
    "GetUserTweetsInput",
    "GetTweetsByIdsInput",
    "GetAllXUsersInput",
    "GetRecentTweetsInput",
]