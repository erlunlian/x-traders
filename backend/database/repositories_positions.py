"""
Repository for position tracking.
"""
import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, select

from database.models import Position


class PositionRepository:
    """
    Repository for position tracking.
    Note: Methods do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_for_buy_without_commit(
        self, trader_id: uuid.UUID, ticker: str, quantity: int, price_in_cents: int
    ):
        """Update position and avg_cost for buy"""
        # Get current position with lock
        result = await self.session.execute(
            select(Position)
            .where(and_(Position.trader_id == trader_id, Position.ticker == ticker))
            .with_for_update()
        )
        position = result.scalar_one_or_none()

        if position:
            # Update avg_cost: (old_qty * old_avg + new_qty * price) / total_qty
            new_qty = position.quantity + quantity
            new_avg = (
                ((position.quantity * position.avg_cost) + (quantity * price_in_cents))
                // new_qty
                if new_qty > 0
                else 0
            )

            position.quantity = new_qty
            position.avg_cost = new_avg
        else:
            # Create new position
            position = Position(
                trader_id=trader_id,
                ticker=ticker,
                quantity=quantity,
                avg_cost=price_in_cents,
            )
            self.session.add(position)

    async def update_for_sell_without_commit(
        self, trader_id: uuid.UUID, ticker: str, quantity: int
    ):
        """Update position for sell - avg_cost remains unchanged"""
        result = await self.session.execute(
            select(Position)
            .where(and_(Position.trader_id == trader_id, Position.ticker == ticker))
            .with_for_update()
        )
        position = result.scalar_one_or_none()

        if not position or position.quantity < quantity:
            raise ValueError(
                f"Insufficient shares: trying to sell {quantity}, have {position.quantity if position else 0}"
            )

        position.quantity -= quantity

    async def get_position(self, trader_id: uuid.UUID, ticker: str) -> Position:
        """Get position - raises if not found"""
        result = await self.session.execute(
            select(Position).where(
                Position.trader_id == trader_id, Position.ticker == ticker
            )
        )
        return result.scalar_one()

    async def get_position_or_none(
        self, trader_id: uuid.UUID, ticker: str
    ) -> Optional[Position]:
        """Get position - returns None if not found"""
        result = await self.session.execute(
            select(Position).where(
                Position.trader_id == trader_id, Position.ticker == ticker
            )
        )
        return result.scalar_one_or_none()

    async def get_all_positions(self, trader_id: uuid.UUID) -> List[Position]:
        """Get all positions for a trader"""
        result = await self.session.execute(
            select(Position)
            .where(Position.trader_id == trader_id)
            .where(Position.quantity > 0)
        )
        return list(result.scalars().all())
