"""
Repository for trader accounts.
"""

import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from database.models import TraderAccount


class TraderRepository:
    """
    Repository for trader accounts.
    Note: Methods do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_trader_in_transaction_without_commit(
        self,
        trader_id: Optional[uuid.UUID] = None,
        is_admin: bool = False,
    ) -> TraderAccount:
        """
        Create a new trader account.
        Must be called within a transaction context - does NOT commit.
        """
        trader = TraderAccount(
            trader_id=trader_id or uuid.uuid4(),
            is_active=True,
            is_admin=is_admin,
        )
        self.session.add(trader)
        await self.session.flush()
        return trader

    async def get_trader(self, trader_id: uuid.UUID) -> TraderAccount:
        """Get trader - raises if not found"""
        result = await self.session.execute(
            select(TraderAccount).where(TraderAccount.trader_id == trader_id)
        )
        return result.scalar_one()

    async def get_trader_or_none(self, trader_id: uuid.UUID) -> Optional[TraderAccount]:
        """Get trader - returns None if not found"""
        result = await self.session.execute(
            select(TraderAccount).where(TraderAccount.trader_id == trader_id)
        )
        return result.scalar_one_or_none()

    async def get_all_traders(self) -> List[TraderAccount]:
        """Get all traders"""
        result = await self.session.execute(
            select(TraderAccount)
            .where(TraderAccount.is_active)
            .order_by(desc(TraderAccount.created_at))
        )
        return list(result.scalars().all())

    async def delete_trader_without_commit(self, trader_id: uuid.UUID) -> bool:
        """Delete a trader account. Returns True if deleted."""
        trader = await self.get_trader_or_none(trader_id)
        if not trader:
            return False
        await self.session.delete(trader)
        await self.session.flush()
        return True
