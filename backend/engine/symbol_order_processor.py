import asyncio
from uuid import UUID

from database import get_db_transaction
from database.repositories import (
    LedgerRepository,
    OrderRepository,
    OutboxRepository,
    PositionRepository,
    TradeRepository,
)
from models.schemas import (
    CancelOrderMessage,
    MessageType,
    NewOrderMessage,
    OrderMessage,
    BookState,
)
from enums import CancelReason, OrderType

from engine.order_book_matcher import OrderBookMatcher


class SymbolOrderProcessor:
    """
    Independent matching engine for one ticker.
    Processes orders sequentially to maintain deterministic price-time priority.
    """

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.matcher = OrderBookMatcher(ticker)
        self.order_queue = asyncio.Queue()
        self.running = False

    async def start(self):
        """Start processing orders from queue"""
        self.running = True
        while self.running:
            try:
                order_msg = await self.order_queue.get()
                await self._process_order_message(order_msg)
            except Exception as e:
                # Log error but keep engine running
                print(f"Error processing order for {self.ticker}: {e}")

    async def stop(self):
        """Stop the engine"""
        self.running = False

    async def submit_order(self, order_id: UUID):
        """Queue order for processing"""
        msg = NewOrderMessage(order_id=order_id)
        await self.order_queue.put(msg)

    async def cancel_order(
        self, order_id: UUID, cancel_reason: CancelReason = CancelReason.USER
    ):
        """Queue order cancellation"""
        msg = CancelOrderMessage(order_id=order_id, cancel_reason=cancel_reason)
        await self.order_queue.put(msg)

    async def _process_order_message(self, msg: OrderMessage):
        """Process order message based on type"""
        if msg.message_type == MessageType.CANCEL_ORDER:
            cancel_msg = CancelOrderMessage(**msg.model_dump())
            await self._process_cancellation(
                cancel_msg.order_id, cancel_msg.cancel_reason
            )
        else:
            await self._process_new_order(msg.order_id)

    async def _process_cancellation(self, order_id: UUID, cancel_reason: CancelReason):
        """Process order cancellation"""
        async with get_db_transaction() as session:
            order_repo = OrderRepository(session)

            try:
                # Update order status in database
                order = await order_repo.cancel_order_without_commit(
                    order_id, cancel_reason
                )

                # Remove from in-memory book
                self.matcher.cancel_order(order)

                # Transaction commits when exiting context manager
            except (ValueError, Exception) as e:
                # Order not found or not cancellable
                print(f"Cannot cancel order {order_id}: {e}")

    async def _process_new_order(self, order_id: UUID):
        """
        Process new order with atomic transaction for:
        - Order matching
        - Trade recording
        - Ledger updates
        - Position updates
        - Market data events
        """
        async with get_db_transaction() as session:
            # Initialize repositories with same session
            order_repo = OrderRepository(session)
            trade_repo = TradeRepository(session)
            ledger_repo = LedgerRepository(session)
            position_repo = PositionRepository(session)
            outbox_repo = OutboxRepository(session)

            # Get order
            order = await order_repo.get_order(order_id)

            # Match order
            trades, remaining = self.matcher.match_order(order)

            # Process each trade
            for trade_data in trades:
                # Record trade
                trade = await trade_repo.record_trade_without_commit(trade_data)

                # Update ledger (double-entry)
                await ledger_repo.post_trade_entries_without_commit(trade)

                # Update positions
                await position_repo.update_for_buy_without_commit(
                    trade_data.buyer_id,
                    self.ticker,
                    trade_data.quantity,
                    trade_data.price_in_cents,
                )
                await position_repo.update_for_sell_without_commit(
                    trade_data.seller_id,
                    self.ticker,
                    trade_data.quantity,
                )

                # Update order fill quantities
                await order_repo.update_filled_without_commit(
                    trade_data.buy_order_id,
                    trade_data.quantity,
                )
                await order_repo.update_filled_without_commit(
                    trade_data.sell_order_id,
                    trade_data.quantity,
                )

                # Queue market data event
                book_state = self.matcher.order_book.get_book_state()
                await outbox_repo.queue_trade_event_without_commit(
                    trade_data,
                    book_state,
                )

                # Update last price
                self.matcher.order_book.last_price_in_cents = trade_data.price_in_cents

            # Add unfilled portion to book (for limit orders)
            if remaining > 0 and order.order_type == OrderType.LIMIT:
                self.matcher.add_order_to_book(order)

            # Commit everything atomically
            await session.commit()

    def get_order_book_snapshot(self):
        """Get current order book snapshot"""
        return self.matcher.order_book.to_snapshot()

    def get_book_state(self) -> BookState:
        """Get current book state for market data"""
        return self.matcher.order_book.get_book_state()

    async def rebuild_book_from_db(self):
        """Rebuild order book from database on startup"""
        async with get_db_transaction() as session:
            order_repo = OrderRepository(session)

            # Get all unfilled orders
            orders = await order_repo.get_unfilled_orders(self.ticker)

            # Sort by sequence to maintain price-time priority
            orders.sort(key=lambda o: o.sequence)

            # Add each to book
            for order in orders:
                self.matcher.add_order_to_book(order)
