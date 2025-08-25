from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from enums import Side
from sortedcontainers import SortedDict


@dataclass
class OrderBookEntry:
    """Single order in the book"""

    order_id: UUID
    trader_id: UUID
    quantity: int
    remaining_quantity: int
    price_in_cents: int
    sequence: int  # For price-time priority
    timestamp: datetime


@dataclass
class OrderBook:
    """In-memory order book for a single ticker"""

    ticker: str
    bids: SortedDict = field(
        default_factory=lambda: SortedDict(lambda x: -x)
    )  # Sorted high to low
    asks: SortedDict = field(default_factory=SortedDict)  # Sorted low to high
    last_price_in_cents: Optional[int] = None

    def add_order(self, side: Side, price_in_cents: int, entry: OrderBookEntry):
        """Add order to the appropriate side of the book"""
        book_side = self.bids if side == Side.BUY else self.asks

        if price_in_cents not in book_side:
            book_side[price_in_cents] = []

        # Add to end of queue at this price level (price-time priority)
        book_side[price_in_cents].append(entry)

    def remove_order(self, side: Side, price_in_cents: int, order_id: UUID) -> bool:
        """Remove a specific order from the book"""
        book_side = self.bids if side == Side.BUY else self.asks

        if price_in_cents not in book_side:
            return False

        orders = book_side[price_in_cents]
        for i, order in enumerate(orders):
            if order.order_id != order_id:
                continue

            orders.pop(i)
            if not orders:  # Remove price level if empty
                del book_side[price_in_cents]
            return True

        return False

    def get_best_bid(self) -> Optional[tuple[int, List[OrderBookEntry]]]:
        """Get best bid price and orders at that level"""
        if not self.bids:
            return None

        price = self.bids.keys()[0]  # Highest bid
        return price, self.bids[price]

    def get_best_ask(self) -> Optional[tuple[int, List[OrderBookEntry]]]:
        """Get best ask price and orders at that level"""
        if not self.asks:
            return None

        price = self.asks.keys()[0]  # Lowest ask
        return price, self.asks[price]

    def get_spread(self) -> Optional[int]:
        """Get bid-ask spread in cents"""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()

        if not best_bid or not best_ask:
            return None

        return best_ask[0] - best_bid[0]

    def get_book_state(self):
        """Get current book state for market data"""
        from models.schemas import BookState

        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()

        return BookState(
            best_bid_in_cents=best_bid[0] if best_bid else None,
            best_ask_in_cents=best_ask[0] if best_ask else None,
            bid_size=(
                sum(o.remaining_quantity for o in best_bid[1]) if best_bid else None
            ),
            ask_size=(
                sum(o.remaining_quantity for o in best_ask[1]) if best_ask else None
            ),
        )

    def to_snapshot(self):
        """Convert to API snapshot format"""
        from models.schemas import OrderBookSnapshot

        bids: Dict[int, int] = {}
        for price, orders in self.bids.items():
            bids[price] = sum(o.remaining_quantity for o in orders)

        asks: Dict[int, int] = {}
        for price, orders in self.asks.items():
            asks[price] = sum(o.remaining_quantity for o in orders)

        return OrderBookSnapshot(
            ticker=self.ticker,
            bids=bids,
            asks=asks,
            last_price_in_cents=self.last_price_in_cents,
            timestamp=datetime.now(timezone.utc),
        )
