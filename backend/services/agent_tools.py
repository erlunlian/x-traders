"""
Tool registry for LangGraph agents to interact with the exchange.
These tools are structured for easy integration with LangChain/LangGraph.
"""
from typing import List
from uuid import UUID

from langchain_core.tools import StructuredTool
from models.core import OrderType
from models.tools import (
    BuyOrderInput,
    SellOrderInput,
    CancelOrderInput,
    GetOrderStatusInput,
    GetPortfolioInput,
    CreateTraderInput,
    GetOrderBookInput,
    GetPriceInput,
    GetRecentTradesInput,
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
from models.responses import (
    CancelResult,
    OrderResult,
    OrderStatusResult,
    PortfolioResult,
    TraderResult,
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
            message=f"Buy order placed for {quantity} shares of {ticker}"
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
            message=f"Sell order placed for {quantity} shares of {ticker}"
        )
    except Exception as e:
        return OrderResult(success=False, message="", error=str(e))


async def cancel_stock_order(trader_id: str, order_id: str) -> CancelResult:
    """Cancel an existing order"""
    try:
        success = await cancel_order(UUID(trader_id), UUID(order_id))
        if success:
            return CancelResult(
                success=True,
                message=f"Order {order_id} cancelled successfully"
            )
        else:
            return CancelResult(
                success=False,
                message="Order cannot be cancelled (already filled or expired)"
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
async def check_order_book(ticker: str) -> dict:
    """Get order book for a ticker showing all bid and ask levels"""
    result = await get_order_book(ticker)
    if result.success:
        return {
            "ticker": result.ticker,
            "bids": [
                {"price_dollars": level.price_in_cents / 100, "quantity": level.quantity}
                for level in result.bids[:5]  # Top 5 levels
            ],
            "asks": [
                {"price_dollars": level.price_in_cents / 100, "quantity": level.quantity}
                for level in result.asks[:5]  # Top 5 levels
            ],
            "last_price_dollars": result.last_price_in_cents / 100 if result.last_price_in_cents else None,
        }
    else:
        return {"error": result.error}


async def check_price(ticker: str) -> dict:
    """Get current price and spread for a ticker"""
    try:
        price = await get_current_price(ticker)
        return {
            "ticker": price.ticker,
            "last_price_dollars": price.last_price_in_cents / 100 if price.last_price_in_cents else None,
            "best_bid_dollars": price.best_bid_in_cents / 100 if price.best_bid_in_cents else None,
            "best_ask_dollars": price.best_ask_in_cents / 100 if price.best_ask_in_cents else None,
            "bid_size": price.bid_size,
            "ask_size": price.ask_size,
            "spread_dollars": price.spread_in_cents / 100 if price.spread_in_cents else None,
        }
    except Exception as e:
        return {"error": str(e)}


async def check_all_prices() -> dict:
    """Get current prices for all tickers"""
    try:
        prices = await get_all_prices()
        return {
            "prices": [
                {
                    "ticker": p.ticker,
                    "last_price_dollars": p.last_price_in_cents / 100 if p.last_price_in_cents else None,
                    "bid_dollars": p.best_bid_in_cents / 100 if p.best_bid_in_cents else None,
                    "ask_dollars": p.best_ask_in_cents / 100 if p.best_ask_in_cents else None,
                    "spread_dollars": p.spread_in_cents / 100 if p.spread_in_cents else None,
                }
                for p in prices
            ]
        }
    except Exception as e:
        return {"error": str(e)}


async def check_recent_trades(ticker: str, limit: int = 20) -> dict:
    """Get recent trades for a ticker"""
    result = await get_recent_trades(ticker, limit)
    if result.success:
        return {
            "ticker": result.ticker,
            "trades": [
                {
                    "price_dollars": trade.price_in_cents / 100,
                    "quantity": trade.quantity,
                    "time": trade.executed_at.isoformat(),
                }
                for trade in result.trades
            ],
        }
    else:
        return {"error": result.error}


async def list_tickers() -> List[str]:
    """Get list of all tradeable tickers"""
    return get_available_tickers()


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