"""
Database utilities for agents to ensure proper async context handling.
Helps prevent SQLAlchemy greenlet context errors in LangGraph execution.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from database import async_session
from database.repositories import AgentRepository, XDataRepository
from models.schemas.agents import Agent
from models.schemas.tweet_feed import TweetForAgent


async def get_agent_safe(agent_id: UUID) -> Agent:
    """
    Get agent with proper session handling.
    Creates and closes session within this function to avoid context issues.
    """
    async with async_session() as session:
        repo = AgentRepository(session)
        agent = await repo.get_agent(agent_id)
        # Return the agent - it's detached from session after context exits
        return agent


async def get_agent_or_none_safe(agent_id: UUID) -> Optional[Agent]:
    """
    Get agent or None with proper session handling.
    Creates and closes session within this function to avoid context issues.
    """
    try:
        async with async_session() as session:
            repo = AgentRepository(session)
            agent = await repo.get_agent_or_none(agent_id)
            # Return the agent - it's detached from session after context exits
            return agent
    except Exception:
        return None


async def get_active_agents_safe() -> List[Agent]:
    """
    Get all active agents with proper session handling.
    Creates and closes session within this function to avoid context issues.
    """
    async with async_session() as session:
        repo = AgentRepository(session)
        agents = await repo.get_active_agents()
        # Return the agents - they're detached from session after context exits
        return agents


async def get_tweets_safe(after_timestamp: Optional[datetime], limit: int) -> List[TweetForAgent]:
    """
    Get tweets with proper session handling.
    Creates and closes session within this function.
    """
    async with async_session() as session:
        repo = XDataRepository(session)
        tweets = await repo.get_tweets_for_agent(after_timestamp, limit)
        # Return the tweets - they're detached from session after context exits
        return tweets


async def update_last_processed_tweet_safe(agent_id: UUID, timestamp: datetime) -> None:
    """
    Update last processed tweet timestamp with proper session handling.
    Creates its own transaction context.
    """
    async with async_session() as session:
        repo = AgentRepository(session)
        await repo.update_last_processed_tweet_without_commit(agent_id, timestamp)
        await session.commit()


async def record_decision_safe(
    agent_id: UUID,
    trigger_type,
    action,
    thoughts: List,
    ticker: Optional[str] = None,
    quantity: Optional[int] = None,
    reasoning: Optional[str] = None,
    trigger_tweet_id: Optional[UUID] = None,
    order_id: Optional[UUID] = None,
    executed: bool = False,
) -> UUID:
    """
    Record a decision with proper session handling.
    Returns the decision_id.
    """
    async with async_session() as session:
        repo = AgentRepository(session)
        decision = await repo.record_decision_without_commit(
            agent_id=agent_id,
            trigger_type=trigger_type,
            action=action,
            thoughts=thoughts,
            ticker=ticker,
            quantity=quantity,
            reasoning=reasoning,
            trigger_tweet_id=trigger_tweet_id,
            order_id=order_id,
            executed=executed,
        )
        await session.commit()
        return decision.decision_id


async def save_orphan_thoughts_safe(agent_id: UUID, thoughts: List) -> None:
    """
    Save orphan thoughts with proper session handling.
    Creates its own transaction context.
    """
    async with async_session() as session:
        repo = AgentRepository(session)

        for thought in thoughts:
            await repo.save_orphan_thought_without_commit(
                agent_id=agent_id,
                thought_type=thought.thought_type,
                content=thought.content,
                step_number=thought.step_number,
            )

        await session.commit()
