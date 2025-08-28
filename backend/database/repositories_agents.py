"""
Repository for AI agent operations.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, desc, func, select

from database.models import AgentDecision, AgentMemory, AgentThought, AIAgent
from enums import (
    AgentAction,
    AgentDecisionTrigger,
    AgentMemoryType,
    AgentThoughtType,
    LLMModel,
)
from models.schemas.agents import (
    Agent,
    AgentMemoryState,
    AgentStats,
    DecisionDetail,
    DecisionInfo,
    MemoryInfo,
    ThoughtInfo,
)


class AgentRepository:
    """Repository for AI agent operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_db_agent(self, agent_id: UUID) -> AIAgent:
        """Get agent database model - internal use only"""
        result = await self.session.execute(
            select(AIAgent).where(AIAgent.agent_id == agent_id)
        )
        return result.scalar_one()

    async def _get_db_agent_or_none(self, agent_id: UUID) -> Optional[AIAgent]:
        """Get agent database model or None - internal use only"""
        result = await self.session.execute(
            select(AIAgent).where(AIAgent.agent_id == agent_id)
        )
        return result.scalar_one_or_none()

    async def get_agent(self, agent_id: UUID) -> Agent:
        """Get agent"""
        agent = await self._get_db_agent(agent_id)
        return self._db_to_agent(agent)

    async def get_agent_by_name(self, name: str) -> Agent:
        """Get agent by name"""
        result = await self.session.execute(select(AIAgent).where(AIAgent.name == name))
        agent = result.scalar_one()
        return self._db_to_agent(agent)

    async def get_agent_or_none(self, agent_id: UUID) -> Optional[Agent]:
        """Get agent database record or None if not found"""
        result = await self.session.execute(
            select(AIAgent).where(AIAgent.agent_id == agent_id)
        )
        agent = result.scalar_one_or_none()
        return self._db_to_agent(agent) if agent else None

    async def get_agent_by_name_or_none(self, name: str) -> Optional[Agent]:
        """Get agent database record by name or None if not found"""
        result = await self.session.execute(select(AIAgent).where(AIAgent.name == name))
        agent = result.scalar_one_or_none()
        return self._db_to_agent(agent) if agent else None

    def _db_to_agent(self, agent: AIAgent) -> Agent:
        """Convert DB model to Pydantic model"""
        return Agent(
            agent_id=agent.agent_id,
            name=agent.name,
            trader_id=agent.trader_id,
            llm_model=agent.llm_model,
            temperature=agent.temperature,
            personality_prompt=agent.personality_prompt,
            is_active=agent.is_active,
            total_decisions=agent.total_decisions,
            last_decision_at=agent.last_decision_at,
            created_at=agent.created_at,
            last_processed_tweet_at=agent.last_processed_tweet_at,
        )

    async def create_agent_without_commit(
        self,
        name: str,
        trader_id: UUID,
        llm_model: LLMModel,
        personality_prompt: str,
        temperature: float = 0.7,
        is_active: bool = True,
    ) -> Agent:
        """Create a new AI agent"""
        agent = AIAgent(
            name=name,
            trader_id=trader_id,
            llm_model=llm_model,
            personality_prompt=personality_prompt,
            temperature=temperature,
            is_active=is_active,
        )
        self.session.add(agent)
        await self.session.flush()

        return self._db_to_agent(agent)

    async def list_agents(
        self,
        trader_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Agent]:
        """List agents with optional filters"""
        query = select(AIAgent)

        if trader_id:
            query = query.where(AIAgent.trader_id == trader_id)
        if is_active is not None:
            query = query.where(AIAgent.is_active == is_active)

        query = query.order_by(desc(AIAgent.created_at)).limit(limit).offset(offset)

        result = await self.session.execute(query)
        agents = result.scalars().all()

        return [self._db_to_agent(agent) for agent in agents]

    async def update_agent_without_commit(
        self,
        agent_id: UUID,
        temperature: Optional[float] = None,
        personality_prompt: Optional[str] = None,
        is_active: Optional[bool] = None,
        llm_model: Optional["LLMModel"] = None,
    ) -> Optional[Agent]:
        """Update agent configuration"""
        agent_db = await self._get_db_agent_or_none(agent_id)

        if not agent_db:
            return None

        if temperature is not None:
            agent_db.temperature = temperature
        if personality_prompt is not None:
            agent_db.personality_prompt = personality_prompt
        if is_active is not None:
            agent_db.is_active = is_active
        if llm_model is not None:
            agent_db.llm_model = llm_model

        await self.session.flush()

        return self._db_to_agent(agent_db)

    async def record_decision_without_commit(
        self,
        agent_id: UUID,
        trigger_type: AgentDecisionTrigger,
        action: AgentAction,
        thoughts: List[tuple[AgentThoughtType, str]],  # (type, content) pairs
        ticker: Optional[str] = None,
        quantity: Optional[int] = None,
        reasoning: Optional[str] = None,
        trigger_tweet_id: Optional[str] = None,
        order_id: Optional[UUID] = None,
        executed: bool = False,
    ) -> DecisionDetail:
        """Record an agent decision with thought trail"""
        # Get agent for name
        agent_db = await self._get_db_agent_or_none(agent_id)
        if not agent_db:
            raise ValueError(f"Agent {agent_id} not found")

        # Create decision record
        decision = AgentDecision(
            agent_id=agent_id,
            trigger_type=trigger_type,
            trigger_tweet_id=trigger_tweet_id,
            action=action,
            ticker=ticker,
            quantity=quantity,
            reasoning=reasoning,
            order_id=order_id,
            executed=executed,
        )
        self.session.add(decision)
        await self.session.flush()

        # Create thought records
        thought_records = []
        for i, (thought_type, content) in enumerate(thoughts):
            thought = AgentThought(
                decision_id=decision.decision_id,
                agent_id=agent_id,
                step_number=i + 1,
                thought_type=thought_type,
                content=content,
            )
            self.session.add(thought)
            thought_records.append(thought)

        await self.session.flush()

        # Update agent stats
        agent_db.total_decisions += 1
        agent_db.last_decision_at = decision.created_at
        await self.session.flush()

        return DecisionDetail(
            decision_id=decision.decision_id,
            agent_id=decision.agent_id,
            agent_name=agent_db.name,
            trigger_type=decision.trigger_type,
            trigger_tweet_id=decision.trigger_tweet_id,
            action=decision.action,
            ticker=decision.ticker,
            quantity=decision.quantity,
            reasoning=decision.reasoning,
            order_id=decision.order_id,
            executed=decision.executed,
            created_at=decision.created_at,
            thoughts=[
                ThoughtInfo(
                    thought_id=t.thought_id,
                    step_number=t.step_number,
                    thought_type=t.thought_type,
                    content=t.content,
                    created_at=t.created_at,
                )
                for t in thought_records
            ],
        )

    async def get_decision(self, decision_id: UUID) -> Optional[DecisionDetail]:
        """Get decision with full thought trail"""
        # Get decision with agent info
        result = await self.session.execute(
            select(AgentDecision)
            .join(AIAgent)
            .where(AgentDecision.decision_id == decision_id)
        )
        decision = result.scalar_one_or_none()

        if not decision:
            return None

        # Get thoughts separately to avoid cartesian product
        thoughts_result = await self.session.execute(
            select(AgentThought)
            .where(AgentThought.decision_id == decision_id)
            .order_by(AgentThought.step_number)
        )
        thoughts = list(thoughts_result.scalars().all())

        return DecisionDetail(
            decision_id=decision.decision_id,
            agent_id=decision.agent_id,
            agent_name=decision.agent.name if decision.agent else "Unknown",
            trigger_type=decision.trigger_type,
            trigger_tweet_id=decision.trigger_tweet_id,
            action=decision.action,
            ticker=decision.ticker,
            quantity=decision.quantity,
            reasoning=decision.reasoning,
            order_id=decision.order_id,
            executed=decision.executed,
            created_at=decision.created_at,
            thoughts=[
                ThoughtInfo(
                    thought_id=t.thought_id,
                    step_number=t.step_number,
                    thought_type=t.thought_type,
                    content=t.content,
                    created_at=t.created_at,
                )
                for t in thoughts
            ],
        )

    async def list_agent_decisions(
        self,
        agent_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DecisionInfo]:
        """List decisions for an agent"""
        query = select(AgentDecision).where(AgentDecision.agent_id == agent_id)

        query = (
            query.order_by(desc(AgentDecision.created_at)).limit(limit).offset(offset)
        )

        result = await self.session.execute(query)
        decisions = result.scalars().all()

        return [
            DecisionInfo(
                decision_id=d.decision_id,
                agent_id=d.agent_id,
                trigger_type=d.trigger_type,
                trigger_tweet_id=d.trigger_tweet_id,
                action=d.action,
                ticker=d.ticker,
                quantity=d.quantity,
                reasoning=d.reasoning,
                order_id=d.order_id,
                executed=d.executed,
                created_at=d.created_at,
            )
            for d in decisions
        ]

    async def save_memory_without_commit(
        self,
        agent_id: UUID,
        memory_type: AgentMemoryType,
        content: str,
        token_count: int,
    ) -> MemoryInfo:
        """Save agent memory snapshot"""
        # If saving working memory, delete old working memory
        if memory_type == AgentMemoryType.WORKING:
            result = await self.session.execute(
                select(AgentMemory).where(
                    and_(
                        AgentMemory.agent_id == agent_id,
                        AgentMemory.memory_type == AgentMemoryType.WORKING,
                    )
                )
            )
            old_working = result.scalar_one_or_none()

            if old_working:
                await self.session.delete(old_working)

        memory = AgentMemory(
            agent_id=agent_id,
            memory_type=memory_type,
            content=content,
            token_count=token_count,
        )
        self.session.add(memory)
        await self.session.flush()

        return MemoryInfo(
            memory_id=memory.memory_id,
            memory_type=memory.memory_type,
            content=memory.content,
            token_count=memory.token_count,
            created_at=memory.created_at,
        )

    async def get_agent_memory(self, agent_id: UUID) -> AgentMemoryState:
        """Get current memory state for an agent"""
        result = await self.session.execute(
            select(AgentMemory)
            .where(AgentMemory.agent_id == agent_id)
            .order_by(desc(AgentMemory.created_at))
        )
        memories = result.scalars().all()

        working_memory = None
        compressed_memories = []
        total_tokens = 0

        for memory in memories:
            memory_info = MemoryInfo(
                memory_id=memory.memory_id,
                memory_type=memory.memory_type,
                content=memory.content,
                token_count=memory.token_count,
                created_at=memory.created_at,
            )

            if memory.memory_type == AgentMemoryType.WORKING:
                working_memory = memory_info
            else:
                compressed_memories.append(memory_info)

            total_tokens += memory.token_count

        return AgentMemoryState(
            agent_id=agent_id,
            working_memory=working_memory,
            compressed_memories=compressed_memories,
            total_tokens=total_tokens,
        )

    async def get_agent_stats(self, agent_id: UUID) -> Optional[AgentStats]:
        """Get comprehensive agent statistics"""
        # Get agent
        agent = await self.get_agent_or_none(agent_id)

        if not agent:
            return None

        # Get action breakdown
        action_counts = await self.session.execute(
            select(
                AgentDecision.action,
                func.count(AgentDecision.decision_id).label("count"),
            )
            .where(AgentDecision.agent_id == agent_id)
            .group_by(AgentDecision.action)
        )

        action_breakdown = {row.action.value: row.count for row in action_counts}

        # Count trade decisions and executed trades
        trade_decisions = await self.session.execute(
            select(func.count(AgentDecision.decision_id)).where(
                and_(
                    AgentDecision.agent_id == agent_id,
                    AgentDecision.action.in_([AgentAction.BUY, AgentAction.SELL]),
                )
            )
        )
        trade_count = trade_decisions.scalar() or 0

        executed_trades = await self.session.execute(
            select(func.count(AgentDecision.decision_id)).where(
                and_(
                    AgentDecision.agent_id == agent_id,
                    AgentDecision.action.in_([AgentAction.BUY, AgentAction.SELL]),
                    AgentDecision.executed,
                )
            )
        )
        executed_count = executed_trades.scalar() or 0

        execution_rate = (
            (executed_count / trade_count * 100) if trade_count > 0 else 0.0
        )

        return AgentStats(
            agent_id=agent.agent_id,
            name=agent.name,
            llm_model=agent.llm_model,
            is_active=agent.is_active,
            total_decisions=agent.total_decisions,
            last_decision_at=agent.last_decision_at,
            action_breakdown=action_breakdown,
            trade_decisions=trade_count,
            executed_trades=executed_count,
            execution_rate=execution_rate,
        )

    async def get_active_agents(self) -> List[Agent]:
        """Get all active agents"""
        result = await self.session.execute(
            select(AIAgent).where(AIAgent.is_active).order_by(AIAgent.name)
        )
        agents = result.scalars().all()

        return [self._db_to_agent(agent) for agent in agents]

    async def update_last_processed_tweet_without_commit(
        self, agent_id: UUID, timestamp: datetime
    ):
        """Update the last processed tweet timestamp for an agent"""
        agent_db = await self._get_db_agent_or_none(agent_id)
        if agent_db:
            agent_db.last_processed_tweet_at = timestamp
            await self.session.flush()

    async def save_orphan_thought_without_commit(
        self,
        agent_id: UUID,
        thought_type: AgentThoughtType,
        content: str,
        step_number: int = 0,
    ):
        """Save a thought that's not associated with a specific decision"""
        thought = AgentThought(
            agent_id=agent_id,
            decision_id=None,  # Orphan thought, not tied to a decision
            step_number=step_number,
            thought_type=thought_type,
            content=content[:2000],  # Truncate to field limit
        )
        self.session.add(thought)
        await self.session.flush()

    async def cleanup_old_memories_without_commit(
        self,
        agent_id: UUID,
        keep_last_n: int = 10,
    ) -> int:
        """Clean up old compressed memories, keeping the most recent N"""
        # Get compressed memories ordered by creation time
        result = await self.session.execute(
            select(AgentMemory)
            .where(
                and_(
                    AgentMemory.agent_id == agent_id,
                    AgentMemory.memory_type == AgentMemoryType.COMPRESSED,
                )
            )
            .order_by(desc(AgentMemory.created_at))
        )
        memories = result.scalars().all()

        # Delete all but the most recent N
        deleted_count = 0
        for memory in memories[keep_last_n:]:
            await self.session.delete(memory)
            deleted_count += 1

        return deleted_count
