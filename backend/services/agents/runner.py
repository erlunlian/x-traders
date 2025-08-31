"""
Standalone runner for AgentManager and exchange background services.

Run this as a separate process from the FastAPI web server.

Usage:
  python -m services.agents.runner
"""

import asyncio
import signal
from contextlib import suppress

from dotenv import load_dotenv

from config import TICKERS
from database import init_db
from engine import OrderExpirationService, order_router
from services.agents.agent_manager import agent_manager


async def _startup() -> tuple[OrderExpirationService, asyncio.Task, asyncio.Task]:
    """
    Initialize DB, engine, and start background services.
    Returns expiration service instance and background tasks to allow shutdown.
    """
    # Initialize database models/migrations context
    await init_db()

    # Initialize order router and processors
    await order_router.initialize(TICKERS)

    # Start order expiration service
    expiration_service = OrderExpirationService(order_router)
    expiration_task = asyncio.create_task(expiration_service.start())

    # Start agent manager and monitor
    await agent_manager.start()
    agent_monitor_task = asyncio.create_task(agent_manager.monitor_agents())

    return expiration_service, expiration_task, agent_monitor_task


async def _shutdown(
    expiration_service: OrderExpirationService,
    expiration_task: asyncio.Task,
    agent_monitor_task: asyncio.Task,
) -> None:
    """Gracefully stop services and cancel background tasks."""
    # Stop agent manager
    await agent_manager.stop()

    # Stop expiration service
    await expiration_service.stop()

    # Shutdown order router
    await order_router.shutdown()

    # Cancel background tasks
    for task in (expiration_task, agent_monitor_task):
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


async def main() -> None:
    load_dotenv()
    print("Starting Agent Runner...")

    expiration_service, expiration_task, agent_monitor_task = await _startup()

    # Handle termination signals for graceful shutdown
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_signal(_: int, __: object) -> None:
        stop_event.set()

    with suppress(NotImplementedError):
        loop.add_signal_handler(signal.SIGINT, _handle_signal, 0, None)
        loop.add_signal_handler(signal.SIGTERM, _handle_signal, 0, None)

    # Wait until signal
    await stop_event.wait()

    print("Shutting down Agent Runner...")
    await _shutdown(expiration_service, expiration_task, agent_monitor_task)
    print("Agent Runner stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Allow quick exit on Ctrl+C
        pass
