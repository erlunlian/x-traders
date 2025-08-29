"""
Repository for order operations.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from database.models import Order, SequenceCounter
from enums import CancelReason, OrderStatus
from models.schemas import OrderRequest


class OrderRepository:
    """
    Repository for order operations.
    Note: Methods do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_next_sequence(self, ticker: str) -> int:
        """Atomic UPSERT for sequence - handles race on first insert"""
        stmt = (
            insert(SequenceCounter)
            .values(ticker=ticker, last_sequence=1)
            .on_conflict_do_update(
                index_elements=["ticker"],
                set_={"last_sequence": SequenceCounter.last_sequence + 1},
            )
            .returning(SequenceCounter.last_sequence)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create_order_without_commit(
        self, order_request: OrderRequest, expires_at: datetime
    ) -> Order:
        """
        Create order with sequence number.
        Must be called within a transaction context - does NOT commit.
        """
        sequence = await self.get_next_sequence(order_request.ticker)

        order = Order(
            trader_id=order_request.trader_id,
            ticker=order_request.ticker,
            side=order_request.side,
            order_type=order_request.order_type,
            quantity=order_request.quantity,
            limit_price=order_request.limit_price_in_cents,
            filled_quantity=0,
            status=OrderStatus.PENDING,
            sequence=sequence,
            tif_seconds=order_request.tif_seconds,
            expires_at=expires_at,
        )
        self.session.add(order)
        await self.session.flush()  # Get ID but stay in transaction
        return order

    async def get_order(self, order_id: uuid.UUID) -> Order:
        """Get order by ID - raises if not found"""
        result = await self.session.execute(select(Order).where(Order.order_id == order_id))
        return result.scalar_one()

    async def get_order_or_none(self, order_id: uuid.UUID) -> Optional[Order]:
        """Get order by ID - returns None if not found"""
        result = await self.session.execute(select(Order).where(Order.order_id == order_id))
        return result.scalar_one_or_none()

    async def update_filled_without_commit(self, order_id: uuid.UUID, fill_quantity: int):
        """
        Update order filled quantity and status.
        Validates that filled quantity doesn't exceed order quantity.
        """
        result = await self.session.execute(
            select(Order).where(Order.order_id == order_id).with_for_update()
        )
        order = result.scalar_one()

        new_filled = order.filled_quantity + fill_quantity
        if new_filled > order.quantity:
            raise ValueError(f"Fill quantity {new_filled} exceeds order quantity {order.quantity}")

        order.filled_quantity = new_filled

        # Update status based on fill
        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
        elif order.filled_quantity > 0:
            order.status = OrderStatus.PARTIAL
        # else stays PENDING

    async def get_unfilled_orders(self, ticker: str) -> List[Order]:
        """Get all unfilled orders for building order book"""
        result = await self.session.execute(
            select(Order)
            .where(Order.ticker == ticker)
            .where(Order.status.in_([OrderStatus.PENDING, OrderStatus.PARTIAL]))
            .order_by(Order.sequence)
        )
        return list(result.scalars().all())

    async def get_trader_unfilled_orders(self, trader_id: uuid.UUID) -> List[Order]:
        """Get all unfilled orders for a specific trader"""
        result = await self.session.execute(
            select(Order)
            .where(Order.trader_id == trader_id)
            .where(Order.status.in_([OrderStatus.PENDING, OrderStatus.PARTIAL]))
            .order_by(desc(Order.created_at))
        )
        return list(result.scalars().all())

    async def get_expired_orders(self, limit: int = 100) -> List[Order]:
        """Get orders that have exceeded their TIF"""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        result = await self.session.execute(
            select(Order)
            .where(Order.expires_at <= now)
            .where(Order.status.in_([OrderStatus.PENDING, OrderStatus.PARTIAL]))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def cancel_order_without_commit(
        self, order_id: uuid.UUID, cancel_reason: CancelReason
    ) -> Order:
        """
        Cancel an order with the specified reason.
        Must be called within a transaction context - does NOT commit.
        Raises if order not found.
        """

        order = await self.get_order(order_id)  # Will raise if not found

        # Only cancel if order is still active
        if order.status not in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
            raise ValueError(f"Cannot cancel order {order_id} with status {order.status}")

        # Update status based on reason
        if cancel_reason == CancelReason.USER:
            order.status = OrderStatus.CANCELLED
        else:
            order.status = OrderStatus.EXPIRED

        order.cancel_reason = cancel_reason
        return order
