"""
Repository for double-entry bookkeeping.
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from database.models import LedgerEntry, Trade


class LedgerRepository:
    """
    Repository for double-entry bookkeeping.
    Note: Methods do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def post_trade_entries_without_commit(self, trade: Trade):
        """Post double-entry for trade execution"""
        # Cash entries
        cash_entries = [
            LedgerEntry(
                trade_id=trade.trade_id,
                trader_id=trade.buyer_id,
                account="CASH",
                debit_in_cents=trade.price * trade.quantity,
                credit_in_cents=0,
                description=f"Buy {trade.quantity} {trade.ticker} @ ${trade.price/100:.2f}",
            ),
            LedgerEntry(
                trade_id=trade.trade_id,
                trader_id=trade.seller_id,
                account="CASH",
                debit_in_cents=0,
                credit_in_cents=trade.price * trade.quantity,
                description=f"Sell {trade.quantity} {trade.ticker} @ ${trade.price/100:.2f}",
            ),
        ]

        # Share entries (stored as quantity, not cents)
        share_entries = [
            LedgerEntry(
                trade_id=trade.trade_id,
                trader_id=trade.buyer_id,
                account=f"SHARES:{trade.ticker}",
                debit_in_cents=trade.quantity,  # Using cents field for quantity
                credit_in_cents=0,
                description=f"Receive {trade.quantity} shares",
            ),
            LedgerEntry(
                trade_id=trade.trade_id,
                trader_id=trade.seller_id,
                account=f"SHARES:{trade.ticker}",
                debit_in_cents=0,
                credit_in_cents=trade.quantity,  # Using cents field for quantity
                description=f"Deliver {trade.quantity} shares",
            ),
        ]

        for entry in cash_entries + share_entries:
            self.session.add(entry)

    async def get_cash_balance_in_cents(self, trader_id: uuid.UUID) -> int:
        """Get current cash balance in cents"""
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(LedgerEntry.debit_in_cents), 0)
                - func.coalesce(func.sum(LedgerEntry.credit_in_cents), 0)
            )
            .where(LedgerEntry.trader_id == trader_id)
            .where(LedgerEntry.account == "CASH")
        )
        return result.scalar() or 0

    async def get_share_balance(self, trader_id: uuid.UUID, ticker: str) -> int:
        """Get share balance (quantity, not cents)"""
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(LedgerEntry.debit_in_cents), 0)
                - func.coalesce(func.sum(LedgerEntry.credit_in_cents), 0)
            )
            .where(LedgerEntry.trader_id == trader_id)
            .where(LedgerEntry.account == f"SHARES:{ticker}")
        )
        return result.scalar() or 0

    async def initialize_trader_cash_without_commit(
        self, trader_id: uuid.UUID, initial_cash_in_cents: int
    ):
        """
        Give trader starting cash.
        Must be called within a transaction context - does NOT commit.
        """
        entry = LedgerEntry(
            trader_id=trader_id,
            account="CASH",
            debit_in_cents=initial_cash_in_cents,
            credit_in_cents=0,
            description=f"Initial deposit: ${initial_cash_in_cents/100:.2f}",
        )
        self.session.add(entry)
