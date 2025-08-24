"""
Portfolio API endpoints for trader positions and balances
"""

from typing import List
from uuid import UUID

from database import async_session
from database.repositories import LedgerRepository, PositionRepository
from engine import order_router
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class PositionResponse(BaseModel):
    """Position information"""

    ticker: str
    quantity: int
    avg_cost_in_cents: int


class PortfolioResponse(BaseModel):
    """Portfolio information"""

    trader_id: UUID
    cash_balance_in_cents: int
    positions: List[PositionResponse]


@router.get("/{trader_id}", response_model=PortfolioResponse)
async def get_portfolio(trader_id: UUID) -> PortfolioResponse:
    """
    Get trader's portfolio including cash balance and positions.
    """
    async with async_session() as session:
        ledger_repo = LedgerRepository(session)
        position_repo = PositionRepository(session)

        # Get cash balance
        cash_balance = await ledger_repo.get_cash_balance_in_cents(trader_id)

        # Get all positions
        positions = await position_repo.get_all_positions(trader_id)

        return PortfolioResponse(
            trader_id=trader_id,
            cash_balance_in_cents=cash_balance,
            positions=[
                PositionResponse(
                    ticker=pos.ticker,
                    quantity=pos.quantity,
                    avg_cost_in_cents=pos.avg_cost,
                )
                for pos in positions
            ],
        )


@router.get("/{trader_id}/position/{ticker}")
async def get_position(trader_id: UUID, ticker: str):
    """
    Get trader's position in a specific ticker.
    """
    if ticker not in order_router.get_tickers():
        raise HTTPException(status_code=404, detail=f"Ticker not found: {ticker}")

    async with async_session() as session:
        position_repo = PositionRepository(session)
        position = await position_repo.get_position(trader_id, ticker)

        return {
            "trader_id": trader_id,
            "ticker": ticker,
            "quantity": position.quantity,
            "avg_cost_in_cents": position.avg_cost,
        }
