"""
Repository for AI agent operations.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, desc, func, select

from database.models import AgentMemory, AgentThought, AIAgent
from enums import AgentMemoryType, AgentThoughtType, AgentToolName, LLMModel
from models.schemas.agents import Agent, AgentMemoryState, AgentStats, MemoryInfo, ThoughtInfo


class AgentRepository:
    """Repository for AI agent operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_db_agent(self, agent_id: UUID) -> AIAgent:
        """Get agent database model - internal use only"""
        result = await self.session.execute(select(AIAgent).where(AIAgent.agent_id == agent_id))
        return result.scalar_one()

    async def _get_db_agent_or_none(self, agent_id: UUID) -> Optional[AIAgent]:
        """Get agent database model or None - internal use only"""
        result = await self.session.execute(select(AIAgent).where(AIAgent.agent_id == agent_id))
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
        result = await self.session.execute(select(AIAgent).where(AIAgent.agent_id == agent_id))
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

    async def update_thought_with_result_without_commit(
        self, thought_id: UUID, result: str
    ) -> None:
        """Update a thought with a result"""
        thought = await self._get_db_thought_or_none(thought_id)
        if thought:
            thought.tool_result = result
            await self.session.flush()

    async def create_thought_without_commit(
        self,
        agent_id: UUID,
        step_number: int,
        thought_type: AgentThoughtType,
        content: str,
        tool_name: Optional[AgentToolName],
        tool_args: Optional[str],
        tool_result: Optional[str],
    ) -> ThoughtInfo:
        """Create a single thought and return ThoughtInfo with ID"""
        thought = AgentThought(
            agent_id=agent_id,
            step_number=step_number,
            thought_type=thought_type,
            content=content,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
        )
        self.session.add(thought)
        await self.session.flush()

        return ThoughtInfo(
            thought_id=thought.thought_id,
            agent_id=thought.agent_id,
            step_number=thought.step_number,
            thought_type=thought.thought_type,
            content=thought.content,
            tool_name=thought.tool_name,
            tool_args=thought.tool_args,
            tool_result=thought.tool_result,
            created_at=thought.created_at,
        )

    async def get_agent_stats(self, agent_id: UUID) -> Optional[AgentStats]:
        """Get comprehensive agent statistics"""
        # Get agent
        agent = await self.get_agent_or_none(agent_id)

        if not agent:
            return None

        # Get thought type breakdown
        thought_counts = await self.session.execute(
            select(
                AgentThought.thought_type,
                func.count(AgentThought.thought_id).label("count"),
            )
            .where(AgentThought.agent_id == agent_id)
            .group_by(AgentThought.thought_type)
        )

        thought_breakdown = {row.thought_type.value: row.count for row in thought_counts}

        # Count total thoughts
        total_thoughts = await self.session.execute(
            select(func.count(AgentThought.thought_id)).where(AgentThought.agent_id == agent_id)
        )
        total_count = total_thoughts.scalar() or 0

        return AgentStats(
            agent_id=agent.agent_id,
            name=agent.name,
            llm_model=agent.llm_model,
            is_active=agent.is_active,
            total_thoughts=total_count,
            thought_breakdown=thought_breakdown,
            last_activity_at=agent.last_decision_at,
        )

    async def get_active_agents(self) -> List[Agent]:
        """Get all active agents"""
        result = await self.session.execute(
            select(AIAgent).where(AIAgent.is_active).order_by(AIAgent.name)
        )
        agents = result.scalars().all()

        return [self._db_to_agent(agent) for agent in agents]

    async def update_last_processed_tweet_without_commit(self, agent_id: UUID, timestamp: datetime):
        """Update the last processed tweet timestamp for an agent"""
        agent_db = await self._get_db_agent_or_none(agent_id)
        if agent_db:
            agent_db.last_processed_tweet_at = timestamp
            await self.session.flush()

    async def list_agent_thoughts(
        self,
        agent_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ThoughtInfo]:
        """Get thoughts timeline for an agent"""
        thoughts_query = (
            select(AgentThought)
            .where(AgentThought.agent_id == agent_id)
            .order_by(AgentThought.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        thoughts_result = await self.session.execute(thoughts_query)
        thoughts = thoughts_result.scalars().all()

        # Convert DB models to ThoughtInfo schema objects
        return [
            ThoughtInfo(
                thought_id=thought.thought_id,
                agent_id=thought.agent_id,
                step_number=thought.step_number,
                thought_type=thought.thought_type,
                content=thought.content,
                tool_name=thought.tool_name,
                tool_args=thought.tool_args,
                tool_result=thought.tool_result,
                created_at=thought.created_at,
            )
            for thought in thoughts
        ]

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
