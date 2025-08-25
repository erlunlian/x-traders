from datetime import datetime, timezone
from typing import List, Tuple

from database.models import DBOrder
from enums import OrderStatus, OrderType, Side
from models.core import OrderBook, OrderBookEntry
from models.schemas import TradeData


class OrderBookMatcher:
    """Price-time priority matching engine"""

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.order_book = OrderBook(ticker=ticker)

    def match_order(self, order: DBOrder) -> Tuple[List[TradeData], int]:
        """
        Match order against book and return trades + remaining quantity.
        Returns: (trades, remaining_quantity)
        """
        match order.order_type:
            case OrderType.IOC:
                return self._match_ioc_order(order)
            case OrderType.MARKET:
                return self._match_market_order(order)
            case OrderType.LIMIT:
                return self._match_limit_order(order)
            case _:
                raise ValueError(f"Invalid order type: {order.order_type}")

    def _match_ioc_order(self, order: DBOrder) -> Tuple[List[TradeData], int]:
        """Match IOC order - fill immediately or cancel"""
        trades, remaining = self._match_aggressive(order)

        # IOC orders don't rest in the book
        if remaining > 0:
            order.status = OrderStatus.EXPIRED
            order.cancel_reason = "IOC_UNFILLED"
            remaining = 0  # Signal not to add to book

        return trades, remaining

    def _match_market_order(self, order: DBOrder) -> Tuple[List[TradeData], int]:
        """Match market order at best available prices"""
        return self._match_aggressive(order)

    def _match_limit_order(self, order: DBOrder) -> Tuple[List[TradeData], int]:
        """Match limit order if price crosses, else add to book"""
        trades = []
        remaining = order.quantity - order.filled_quantity

        opposite_book = (
            self.order_book.asks if order.side == Side.BUY else self.order_book.bids
        )

        while remaining > 0 and opposite_book:
            # Check if limit price crosses
            if order.side == Side.BUY:
                best_price = opposite_book.keys()[0]  # Lowest ask
                if best_price > order.limit_price:
                    break  # Can't match at this price
            else:  # SELL
                best_price = opposite_book.keys()[0]  # Highest bid
                if best_price < order.limit_price:
                    break  # Can't match at this price

            # Match at this price level
            level_trades, remaining = self._match_at_price_level(
                order, opposite_book, best_price, remaining
            )
            trades.extend(level_trades)

        return trades, remaining

    def _match_aggressive(self, order: DBOrder) -> Tuple[List[TradeData], int]:
        """Match aggressively against opposite side (for market/IOC orders)"""
        trades = []
        remaining = order.quantity - order.filled_quantity

        opposite_book = (
            self.order_book.asks if order.side == Side.BUY else self.order_book.bids
        )

        while remaining > 0 and opposite_book:
            best_price = opposite_book.keys()[0]
            level_trades, remaining = self._match_at_price_level(
                order, opposite_book, best_price, remaining
            )
            trades.extend(level_trades)

        return trades, remaining

    def _match_at_price_level(
        self,
        taker_order: DBOrder,
        opposite_book: dict,
        price_in_cents: int,
        remaining_qty: int,
    ) -> Tuple[List[TradeData], int]:
        """Match order against all orders at a specific price level"""
        if price_in_cents not in opposite_book:
            return [], remaining_qty

        trades = []
        orders_at_level = opposite_book[
            price_in_cents
        ].copy()  # Copy to avoid mutation during iteration

        for maker_entry in orders_at_level:
            if remaining_qty <= 0:
                break

            # Calculate fill quantity
            fill_qty = min(remaining_qty, maker_entry.remaining_quantity)

            # Create trade
            trade = self._create_trade(
                taker_order, maker_entry, fill_qty, price_in_cents
            )
            trades.append(trade)

            # Update quantities
            remaining_qty -= fill_qty
            maker_entry.remaining_quantity -= fill_qty

            # Remove filled maker order from book
            if maker_entry.remaining_quantity == 0:
                opposite_book[price_in_cents].remove(maker_entry)

        # Clean up empty price level
        if price_in_cents in opposite_book and not opposite_book[price_in_cents]:
            del opposite_book[price_in_cents]

        return trades, remaining_qty

    def _create_trade(
        self,
        taker_order: DBOrder,
        maker_entry: OrderBookEntry,
        quantity: int,
        price_in_cents: int,
    ) -> TradeData:
        """Create trade record with maker/taker info"""
        if taker_order.side == Side.BUY:
            return TradeData(
                buy_order_id=taker_order.order_id,
                sell_order_id=maker_entry.order_id,
                ticker=self.ticker,
                price_in_cents=price_in_cents,
                quantity=quantity,
                buyer_id=taker_order.trader_id,
                seller_id=maker_entry.trader_id,
                taker_order_id=taker_order.order_id,
                maker_order_id=maker_entry.order_id,
                executed_at=datetime.now(timezone.utc),
            )
        else:
            return TradeData(
                buy_order_id=maker_entry.order_id,
                sell_order_id=taker_order.order_id,
                ticker=self.ticker,
                price_in_cents=price_in_cents,
                quantity=quantity,
                buyer_id=maker_entry.trader_id,
                seller_id=taker_order.trader_id,
                taker_order_id=taker_order.order_id,
                maker_order_id=maker_entry.order_id,
                executed_at=datetime.now(timezone.utc),
            )

    def add_order_to_book(self, order: DBOrder):
        """Add unfilled limit order to book"""
        if order.order_type != OrderType.LIMIT:
            return  # Only limit orders rest in book

        if order.filled_quantity >= order.quantity:
            return  # Fully filled

        entry = OrderBookEntry(
            order_id=order.order_id,
            trader_id=order.trader_id,
            quantity=order.quantity,
            remaining_quantity=order.quantity - order.filled_quantity,
            price_in_cents=order.limit_price,
            sequence=order.sequence,
            timestamp=order.created_at,
        )

        self.order_book.add_order(order.side, order.limit_price, entry)

    def cancel_order(self, order: DBOrder) -> bool:
        """Remove order from book"""
        if order.order_type != OrderType.LIMIT:
            return False

        return self.order_book.remove_order(
            order.side, order.limit_price, order.order_id
        )
