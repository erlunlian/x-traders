"""
AI Agents API endpoints
"""

from typing import List, Optional
from uuid import UUID

from database import async_session
from database.repositories import LedgerRepository
from database.repositories_agents import AgentRepository
from database.repositories_traders import TraderRepository
from enums import LLMModel
from fastapi import APIRouter, HTTPException
from models.schemas.agents import (
    Agent,
    AgentListResponse,
    AgentMemoryState,
    AgentStats,
    CreateAgentRequest,
    DecisionDetail,
    DecisionListResponse,
    UpdateAgentRequest,
)

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
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            is_active=request.is_active,
        )

        await session.commit()
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


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: UUID) -> Agent:
    """
    Get details for a specific agent.
    """
    async with async_session() as session:
        agent_repo = AgentRepository(session)

        agent = await agent_repo.get_agent_or_none(agent_id)
        if not agent:
            raise HTTPException(
                status_code=404, detail=f"Agent not found: {agent_id}"
            )

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
            system_prompt=request.system_prompt,
            is_active=request.is_active,
        )

        if not agent:
            raise HTTPException(
                status_code=404, detail=f"Agent not found: {agent_id}"
            )

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
            raise HTTPException(
                status_code=404, detail=f"Agent not found: {agent_id}"
            )

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
            raise HTTPException(
                status_code=404, detail=f"Agent not found: {agent_id}"
            )

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
            raise HTTPException(
                status_code=404, detail=f"Decision not found: {decision_id}"
            )

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
            raise HTTPException(
                status_code=404, detail=f"Agent not found: {agent_id}"
            )

        memory_state = await agent_repo.get_agent_memory(agent_id)
        return memory_state


@router.get("/models/available", response_model=List[dict])
async def get_available_models() -> List[dict]:
    """
    Get list of available LLM models for agents.
    """
    models = []
    for model in LLMModel:
        provider = "Unknown"
        if "gpt" in model.value.lower():
            provider = "OpenAI"
        elif "claude" in model.value.lower():
            provider = "Anthropic"
        elif "grok" in model.value.lower():
            provider = "xAI"

        models.append({
            "id": model.name,
            "value": model.value,
            "provider": provider,
            "display_name": model.name.replace("_", " ").title(),
        })

    return models
