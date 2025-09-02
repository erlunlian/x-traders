import asyncio
import contextlib
from datetime import datetime, time, timedelta, timezone

from database import get_db_transaction
from database.repositories_agents import AgentRepository
from database.repositories_x_data import XDataRepository


class DailyMaintenanceService:
    """
    Runs daily maintenance jobs at a fixed UTC time.
    Jobs:
      - Prune old tweets, keep most recent N globally
      - Prune agent thoughts, keep most recent N per agent
    """

    DEFAULT_TWEETS_TO_KEEP = 500
    DEFAULT_THOUGHTS_TO_KEEP = 500

    def __init__(self, run_at_utc: time | None = None):
        # Set default run time to 03:00 AM Eastern Standard Time (EST)
        est = timezone(timedelta(hours=-5), "EST")
        self.run_at_utc = run_at_utc or time(3, 0, 0, tzinfo=est)  # 03:00 EST default
        self.running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self.running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self.running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _run_loop(self) -> None:
        while self.running:
            try:
                # Sleep until next scheduled time
                await self._sleep_until_next_run()
                if not self.running:
                    break
                await self._run_jobs_once()
            except Exception as e:
                # Swallow errors to keep loop alive
                print(f"Maintenance service error: {e}")
                await asyncio.sleep(5)

    async def _sleep_until_next_run(self) -> None:
        now = datetime.now(timezone.utc)
        today_run = datetime.combine(now.date(), self.run_at_utc)
        next_run = today_run if now < today_run else today_run + timedelta(days=1)
        sleep_seconds = (next_run - now).total_seconds()
        if sleep_seconds > 0:
            await asyncio.sleep(sleep_seconds)

    async def _run_jobs_once(self) -> None:
        # Tweets prune
        async with get_db_transaction() as session:
            x_repo = XDataRepository(session)
            deleted_tweets = await x_repo.prune_tweets_without_commit(self.DEFAULT_TWEETS_TO_KEEP)
            # transaction commits on context exit
            print(f"Pruned tweets: {deleted_tweets}")

        # Thoughts prune (per agent)
        async with get_db_transaction() as session:
            agent_repo = AgentRepository(session)
            deleted_thoughts = await agent_repo.prune_agent_thoughts_without_commit(
                self.DEFAULT_THOUGHTS_TO_KEEP
            )
            print(f"Pruned agent thoughts: {deleted_thoughts}")
