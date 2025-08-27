import asyncio
from typing import Dict, List
from uuid import UUID

from engine.symbol_order_processor import SymbolOrderProcessor
from models.schemas import OrderBookSnapshot


class OrderRouter:
    """
    Routes orders to the appropriate symbol order processor.
    Manages lifecycle of all symbol processors.
    """

    def __init__(self) -> None:
        self.processors: Dict[str, SymbolOrderProcessor] = {}
        self.processor_tasks: Dict[str, asyncio.Task] = {}

    async def initialize(self, tickers: List[str]) -> None:
        """
        Create and start order processors for each ticker.
        Rebuild order books from database.
        """
        for ticker in tickers:
            # Create processor
            processor = SymbolOrderProcessor(ticker)
            self.processors[ticker] = processor

            # Rebuild book from database
            await processor.rebuild_book_from_db()

            # Start processor task
            task = asyncio.create_task(processor.start())
            self.processor_tasks[ticker] = task

    async def shutdown(self) -> None:
        """Stop all processors gracefully"""
        # Stop all processors
        for processor in self.processors.values():
            await processor.stop()

        # Cancel all tasks
        for task in self.processor_tasks.values():
            task.cancel()

        # Wait for all tasks to complete
        await asyncio.gather(*self.processor_tasks.values(), return_exceptions=True)

    async def submit_order(self, order_id: UUID, ticker: str) -> None:
        """Route order to correct processor"""
        if ticker not in self.processors:
            raise ValueError(f"No processor for ticker: {ticker}")

        await self.processors[ticker].submit_order(order_id)

    async def cancel_order(self, order_id: UUID, ticker: str, cancel_reason=None) -> None:
        """Route cancellation to correct processor"""
        from models.core import CancelReason

        if ticker not in self.processors:
            raise ValueError(f"No processor for ticker: {ticker}")

        if cancel_reason is None:
            cancel_reason = CancelReason.USER

        await self.processors[ticker].cancel_order(order_id, cancel_reason)

    def get_order_book(self, ticker: str) -> OrderBookSnapshot:
        """Get order book snapshot for a ticker"""
        if ticker not in self.processors:
            raise ValueError(f"No processor for ticker: {ticker}")

        return self.processors[ticker].get_order_book_snapshot()

    def get_all_order_books(self) -> Dict[str, OrderBookSnapshot]:
        """Get all order book snapshots"""
        return {
            ticker: processor.get_order_book_snapshot()
            for ticker, processor in self.processors.items()
        }

    def get_tickers(self) -> List[str]:
        """Get list of active tickers"""
        return list(self.processors.keys())
