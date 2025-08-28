"""
AI Agents API endpoints
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException

from database import async_session
from database.repositories import LedgerRepository, PositionRepository
from database.repositories_agents import AgentRepository
from database.repositories_traders import TraderRepository
from database.repositories_trades import TradeRepository
from sqlalchemy import func
from sqlmodel import select
from enums import LLMModel
from models.schemas.agents import (
    Agent,
    AgentLeaderboardEntry,
    AgentLeaderboardResponse,
    AgentListResponse,
    AgentMemoryState,
    AgentStats,
    CreateAgentRequest,
    DecisionDetail,
    DecisionListResponse,
    UpdateAgentRequest,
)
from services.agents.agent_manager import agent_manager

router = APIRouter()


@router.post("/", response_model=Agent)
async def create_agent(request: CreateAgentRequest) -> Agent:
    """
    Create a new AI agent along with a new trader account.
    """
    async with async_session() as session:
        trader_repo = TraderRepository(session)
        agent_repo = AgentRepository(session)
        ledger_repo = LedgerRepository(session)

        # Check if agent name already exists
        existing = await agent_repo.get_agent_by_name_or_none(request.name)
        if existing:
            raise HTTPException(
                status_code=400, detail=f"Agent name already exists: {request.name}"
            )

        # Create new trader account for the agent
        trader = await trader_repo.create_trader_in_transaction_without_commit(
            is_admin=False  # Agent traders are not admin
        )

        # Create initial cash balance for the trader
        await ledger_repo.initialize_trader_cash_without_commit(
            trader_id=trader.trader_id,
            initial_cash_in_cents=request.initial_balance_in_cents,
        )

        # Create agent
        agent = await agent_repo.create_agent_without_commit(
            name=request.name,
            trader_id=trader.trader_id,
            llm_model=request.llm_model,
            personality_prompt=request.personality_prompt,
            temperature=request.temperature,
            is_active=request.is_active,
        )

        await session.commit()

        # Start the agent if it's active
        if agent.is_active:
            await agent_manager.start_agent(agent)

        return agent


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    trader_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> AgentListResponse:
    """
    List all agents with optional filters.
    """
    async with async_session() as session:
        agent_repo = AgentRepository(session)

        agents = await agent_repo.list_agents(
            trader_id=trader_id,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

        return AgentListResponse(agents=agents, total=len(agents))


@router.get("/status", response_model=List[dict])
async def get_all_agent_statuses() -> List[dict]:
    """
    Get the running status of all agents.
    """
    return await agent_manager.get_all_agent_statuses()


@router.get("/leaderboard", response_model=AgentLeaderboardResponse)
async def get_agent_leaderboard() -> AgentLeaderboardResponse:
    """
    Get agent leaderboard with performance metrics.
    """
    async with async_session() as session:
        agent_repo = AgentRepository(session)
        ledger_repo = LedgerRepository(session)
        position_repo = PositionRepository(session)
        trade_repo = TradeRepository(session)
        
        # Get all agents
        agents = await agent_repo.list_agents(limit=1000)
        
        leaderboard_entries = []
        for agent in agents:
            # Get current cash balance
            balance = await ledger_repo.get_cash_balance_in_cents(agent.trader_id)
            
            # Get positions and calculate total value
            positions = await position_repo.get_all_positions(agent.trader_id)
            
            # For now, we'll use a simplified calculation
            # In a real system, we'd need to get current market prices
            total_position_value = sum(
                pos.quantity * pos.avg_cost for pos in positions
            )
            
            total_assets_value = balance + total_position_value
            
            # Count total trades executed
            trades = await trade_repo.get_trader_trades(agent.trader_id, limit=10000)
            total_trades = len(trades)
            
            # Calculate profit/loss (assuming initial balance was $100,000)
            initial_balance = 10000000  # $100,000 in cents
            profit_loss = balance - initial_balance
            
            entry = AgentLeaderboardEntry(
                agent_id=agent.agent_id,
                name=agent.name,
                trader_id=agent.trader_id,
                llm_model=agent.llm_model,
                is_active=agent.is_active,
                balance_in_cents=balance,
                total_assets_value_in_cents=total_assets_value,
                total_trades_executed=total_trades,
                total_decisions=agent.total_decisions,
                profit_loss_in_cents=profit_loss,
                created_at=agent.created_at,
                last_decision_at=agent.last_decision_at,
            )
            leaderboard_entries.append(entry)
        
        # Sort by total assets value by default
        leaderboard_entries.sort(
            key=lambda x: x.total_assets_value_in_cents, reverse=True
        )
        
        return AgentLeaderboardResponse(
            agents=leaderboard_entries,
            total=len(leaderboard_entries),
        )


@router.get("/models/available", response_model=List[dict])
async def get_available_models() -> List[dict]:
    """
    Get list of available LLM models for agents.
    """
    models = []
    for model in LLMModel:
        models.append(
            {
                "id": model.name,
                "value": model.value,
                "provider": model.get_provider().value,
                "display_name": model.name.replace("_", " ").title(),
            }
        )

    return models


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: UUID) -> Agent:
    """
    Get details for a specific agent.
    """
    async with async_session() as session:
        agent_repo = AgentRepository(session)

        agent = await agent_repo.get_agent_or_none(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

        return agent


@router.put("/{agent_id}", response_model=Agent)
async def update_agent(agent_id: UUID, request: UpdateAgentRequest) -> Agent:
    """
    Update agent configuration.
    """
    async with async_session() as session:
        agent_repo = AgentRepository(session)

        agent = await agent_repo.update_agent_without_commit(
            agent_id=agent_id,
            temperature=request.temperature,
            personality_prompt=request.personality_prompt,
            is_active=request.is_active,
            llm_model=request.llm_model,
        )

        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

        await session.commit()
        return agent


@router.get("/{agent_id}/stats", response_model=AgentStats)
async def get_agent_stats(agent_id: UUID) -> AgentStats:
    """
    Get comprehensive statistics for an agent.
    """
    async with async_session() as session:
        agent_repo = AgentRepository(session)

        stats = await agent_repo.get_agent_stats(agent_id)
        if not stats:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

        return stats


@router.get("/{agent_id}/decisions", response_model=DecisionListResponse)
async def get_agent_decisions(
    agent_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> DecisionListResponse:
    """
    Get decision history for an agent.
    """
    async with async_session() as session:
        agent_repo = AgentRepository(session)

        # Verify agent exists
        agent = await agent_repo.get_agent_or_none(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

        decisions = await agent_repo.list_agent_decisions(
            agent_id=agent_id,
            limit=limit,
            offset=offset,
        )

        return DecisionListResponse(
            decisions=decisions,
            total=len(decisions),
            limit=limit,
            offset=offset,
        )


@router.get("/{agent_id}/decisions/{decision_id}", response_model=DecisionDetail)
async def get_decision_detail(agent_id: UUID, decision_id: UUID) -> DecisionDetail:
    """
    Get detailed information about a specific decision including thought trail.
    """
    async with async_session() as session:
        agent_repo = AgentRepository(session)

        decision = await agent_repo.get_decision(decision_id)
        if not decision:
            raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")

        if decision.agent_id != agent_id:
            raise HTTPException(
                status_code=404,
                detail=f"Decision {decision_id} does not belong to agent {agent_id}",
            )

        return decision


@router.get("/{agent_id}/memory", response_model=AgentMemoryState)
async def get_agent_memory(agent_id: UUID) -> AgentMemoryState:
    """
    Get current memory state for an agent.
    """
    async with async_session() as session:
        agent_repo = AgentRepository(session)

        # Verify agent exists
        agent = await agent_repo.get_agent_or_none(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

        memory_state = await agent_repo.get_agent_memory(agent_id)
        return memory_state


@router.post("/{agent_id}/toggle", response_model=Agent)
async def toggle_agent(agent_id: UUID) -> Agent:
    """
    Toggle agent's active status (pause/resume).
    """
    async with async_session() as session:
        agent_repo = AgentRepository(session)

        # Get current agent
        agent = await agent_repo.get_agent_or_none(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

        # Toggle is_active status
        new_status = not agent.is_active
        updated_agent = await agent_repo.update_agent_without_commit(
            agent_id=agent_id,
            is_active=new_status,
        )

        await session.commit()

        # Start or stop the agent in the manager
        if new_status:
            await agent_manager.start_agent(updated_agent)
        else:
            # The agent will stop itself when it detects is_active=False
            pass

        return updated_agent






