"""
Repository for trade operations.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, or_, select

from database.models import Trade
from models.schemas import TradeData


class TradeRepository:
    """
    Repository for trade operations.
    Note: Methods do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_trade_without_commit(self, trade_data: TradeData) -> Trade:
        """
        Record trade execution.
        Must be called within a transaction context - does NOT commit.
        """
        trade = Trade(
            buy_order_id=trade_data.buy_order_id,
            sell_order_id=trade_data.sell_order_id,
            ticker=trade_data.ticker,
            price=trade_data.price_in_cents,
            quantity=trade_data.quantity,
            buyer_id=trade_data.buyer_id,
            seller_id=trade_data.seller_id,
            taker_order_id=trade_data.taker_order_id,
            maker_order_id=trade_data.maker_order_id,
            executed_at=trade_data.executed_at or datetime.now(timezone.utc),
        )
        self.session.add(trade)
        await self.session.flush()
        return trade

    async def get_recent_trades(self, ticker: str, limit: int = 50) -> List[Trade]:
        result = await self.session.execute(
            select(Trade)
            .where(Trade.ticker == ticker)
            .order_by(desc(Trade.executed_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_trader_trades(
        self, trader_id: uuid.UUID, limit: int = 50
    ) -> List[Trade]:
        """Get recent trades for a specific trader (as buyer or seller)"""
        result = await self.session.execute(
            select(Trade)
            .where(or_(Trade.buyer_id == trader_id, Trade.seller_id == trader_id))
            .order_by(desc(Trade.executed_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_ohlc_history(
        self, ticker: str, interval: str, periods: int
    ) -> List[Dict]:
        """
        Get OHLC (Open, High, Low, Close) data for a ticker.

        Args:
            ticker: The ticker symbol
            interval: PostgreSQL interval string (e.g., '1 hour', '1 day', '1 week')
            periods: Number of periods to return

        Returns:
            List of dicts with timestamp, open, high, low, close, volume
        """
        from datetime import datetime, timedelta, timezone

        # Determine time window and truncation
        now = datetime.now(timezone.utc)
        if interval == "1 hour":
            start_time = now - timedelta(hours=periods)
            trunc = "hour"
        elif interval == "6 hours":
            start_time = now - timedelta(hours=periods * 6)
            trunc = "hour"  # Still truncate by hour, but we'll group by 6-hour periods
        elif interval == "1 day":
            start_time = now - timedelta(days=periods)
            trunc = "day"
        elif interval == "1 week":
            start_time = now - timedelta(weeks=periods)
            trunc = "week"
        else:
            # Default fallback
            start_time = now - timedelta(days=30)
            trunc = "day"

        # Simpler query using GROUP BY instead of window functions for the main aggregation
        from sqlalchemy import text

        query = text(
            """
            WITH time_periods AS (
                SELECT 
                    date_trunc(:trunc, executed_at) AS period,
                    MIN(executed_at) AS first_trade_time,
                    MAX(executed_at) AS last_trade_time
                FROM trades
                WHERE ticker = :ticker
                    AND executed_at >= :start_time
                GROUP BY date_trunc(:trunc, executed_at)
            ),
            period_ohlc AS (
                SELECT 
                    tp.period,
                    -- Get first trade price (open)
                    (SELECT price FROM trades 
                     WHERE ticker = :ticker 
                       AND executed_at = tp.first_trade_time 
                     LIMIT 1) AS open,
                    -- Get last trade price (close)
                    (SELECT price FROM trades 
                     WHERE ticker = :ticker 
                       AND executed_at = tp.last_trade_time 
                     LIMIT 1) AS close,
                    -- Get high/low/volume for the period
                    MAX(t.price) AS high,
                    MIN(t.price) AS low,
                    SUM(t.quantity) AS volume
                FROM time_periods tp
                JOIN trades t ON t.ticker = :ticker 
                    AND date_trunc(:trunc, t.executed_at) = tp.period
                GROUP BY tp.period, tp.first_trade_time, tp.last_trade_time
            )
            SELECT 
                period AS timestamp,
                open,
                high,
                low,
                close,
                volume
            FROM period_ohlc
            ORDER BY period ASC
        """
        )

        result = await self.session.execute(
            query,
            {
                "ticker": ticker,
                "trunc": trunc,
                "start_time": start_time,
            },
        )

        rows = result.fetchall()

        # Convert to list of dicts
        ohlc_data = []
        for row in rows:
            ohlc_data.append(
                {
                    "timestamp": row.timestamp,
                    "open": row.open,
                    "high": row.high,
                    "low": row.low,
                    "close": row.close,
                    "volume": int(row.volume) if row.volume else 0,
                }
            )

        # If we need to group 6-hour periods, do it in Python
        if interval == "6 hours":
            grouped_data = []
            i = 0
            while i < len(ohlc_data):
                # Take up to 6 hourly candles and combine them
                group = ohlc_data[i : min(i + 6, len(ohlc_data))]
                if group:
                    grouped_data.append(
                        {
                            "timestamp": group[0]["timestamp"],
                            "open": group[0]["open"],
                            "high": max(g["high"] for g in group),
                            "low": min(g["low"] for g in group),
                            "close": group[-1]["close"],
                            "volume": sum(g["volume"] for g in group),
                        }
                    )
                i += 6
            ohlc_data = grouped_data

        return ohlc_data
