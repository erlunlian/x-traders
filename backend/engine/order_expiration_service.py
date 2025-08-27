import asyncio

from database import async_session
from database.repositories import OrderRepository
from engine.order_router import OrderRouter


class OrderExpirationService:
    """
    Manages order expiration based on Time-In-Force.
    Periodically checks for expired orders and cancels them.
    """

    def __init__(self, order_router: OrderRouter):
        self.order_router = order_router
        self.running = False
        self.check_interval = 1  # Check every second

    async def start(self):
        """Start the expiration checker loop"""
        self.running = True
        await self._run_expiry_loop()

    async def stop(self):
        """Stop the expiration checker"""
        self.running = False

    async def _run_expiry_loop(self):
        """
        Main loop that checks for expired orders.
        Uses the expires_at index for efficient queries.
        """
        while self.running:
            try:
                await self._check_and_expire_orders()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                print(f"Order expiration service error: {e}")
                await asyncio.sleep(self.check_interval)

    async def _check_and_expire_orders(self):
        """Find and expire orders that have exceeded their TIF"""
        # Get expired orders (read-only, no transaction needed)
        async with async_session() as session:
            order_repo = OrderRepository(session)
            expired_orders = await order_repo.get_expired_orders(limit=100)

        if not expired_orders:
            return

        # Send cancellation to each order's engine
        # The engine will handle the transaction when processing the cancel
        from models.core import CancelReason

        for order in expired_orders:
            try:
                await self.order_router.cancel_order(
                    order.order_id, order.ticker, CancelReason.EXPIRED
                )
            except Exception as e:
                print(f"Failed to expire order {order.order_id}: {e}")
