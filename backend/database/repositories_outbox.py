"""
Repository for market data outbox pattern.
"""
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from database.models import MarketDataOutbox
from enums import MarketDataEventType
from models.schemas import BookState, TradeData


class OutboxRepository:
    """
    Repository for market data outbox pattern.
    Note: Methods do NOT commit except publish_batch which is autonomous.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def queue_trade_event_without_commit(
        self, trade_data: TradeData, book_state: BookState
    ):
        """
        Queue trade event with book state.
        Does NOT commit - must be called within trade transaction.
        """
        event = MarketDataOutbox(
            event_type=MarketDataEventType.TRADE,
            ticker=trade_data.ticker,
            payload={
                "trade": {
                    "price_in_cents": trade_data.price_in_cents,
                    "quantity": trade_data.quantity,
                    "timestamp": (
                        trade_data.executed_at or datetime.now(timezone.utc)
                    ).isoformat(),
                },
                "book": {
                    "best_bid_in_cents": book_state.best_bid_in_cents,
                    "best_ask_in_cents": book_state.best_ask_in_cents,
                    "bid_size": book_state.bid_size,
                    "ask_size": book_state.ask_size,
                },
            },
        )
        self.session.add(event)

    async def publish_batch_with_commit(
        self, redis_client=None, limit: int = 100
    ) -> int:
        """
        Atomically claim and publish outbox events.
        This DOES commit as it's a separate autonomous transaction.
        Uses skip_locked to allow multiple workers without contention.
        """
        # Use FOR UPDATE SKIP LOCKED to avoid contention between workers
        result = await self.session.execute(
            select(MarketDataOutbox)
            .where(~MarketDataOutbox.published)
            .order_by(MarketDataOutbox.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)  # Skip rows locked by other workers
        )
        events = result.scalars().all()

        if events and redis_client:
            # Publish to Redis/WebSocket
            for event in events:
                channel = f"{event.event_type.value.lower()}.{event.ticker}"
                await redis_client.publish(channel, event.payload)

            # Mark as published
            event_ids = [e.event_id for e in events]
            await self.session.execute(
                update(MarketDataOutbox)
                .where(MarketDataOutbox.event_id.in_(event_ids))
                .values(published=True)
            )
            await self.session.commit()  # Autonomous commit for outbox

        return len(events)
