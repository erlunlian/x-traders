import asyncio
from typing import Optional

import redis.asyncio as redis
from database import async_session
from database.repositories import OutboxRepository


class MarketDataPublisher:
    """
    Publishes market data events from the outbox table.
    Uses aggressive batching when busy, backs off when idle.
    """

    def __init__(self, redis_url: str):
        self.redis_client: Optional[redis.Redis] = None
        self.redis_url = redis_url
        self.running = False

    async def start(self):
        """Initialize Redis connection and start publisher loop"""
        self.redis_client = await redis.from_url(self.redis_url)
        self.running = True
        await self._run_publisher_loop()

    async def stop(self):
        """Stop publisher and close connections"""
        self.running = False
        if self.redis_client:
            await self.redis_client.close()

    async def _run_publisher_loop(self):
        """
        Main publisher loop with adaptive batching.
        Processes aggressively when busy, backs off when idle.
        """
        consecutive_empty_batches = 0

        while self.running:
            try:
                # Create new session for each batch
                async with async_session() as session:
                    outbox_repo = OutboxRepository(session)

                    # Publish batch (this commits autonomously)
                    published_count = await outbox_repo.publish_batch_with_commit(
                        redis_client=self.redis_client, limit=100
                    )

                # Adaptive sleep based on activity
                if published_count >= 100:
                    # Full batch - process immediately
                    consecutive_empty_batches = 0
                    continue

                if published_count > 0:
                    # Partial batch - short delay
                    consecutive_empty_batches = 0
                    await asyncio.sleep(0.01)  # 10ms
                    continue

                # Empty batch - progressive backoff
                consecutive_empty_batches += 1
                if consecutive_empty_batches < 10:
                    await asyncio.sleep(0.1)  # 100ms
                else:
                    await asyncio.sleep(1.0)  # 1 second max backoff

            except Exception as e:
                print(f"Market data publisher error: {e}")
                await asyncio.sleep(1.0)  # Error backoff
