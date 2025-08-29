"""
Database utilities for agents to ensure proper async context handling.
Helps prevent SQLAlchemy greenlet context errors in LangGraph execution.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from database import async_session
from database.repositories import AgentRepository, XDataRepository
from enums import AgentThoughtType, AgentToolName
from models.schemas.agents import Agent, ThoughtInfo
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


async def create_thought_safe(
    agent_id: UUID,
    step_number: int,
    thought_type: AgentThoughtType,
    content: str,
    tool_name: Optional[AgentToolName],
    tool_args: Optional[str],
    tool_result: Optional[str],
) -> ThoughtInfo:
    """
    Create a single thought and return ThoughtInfo with ID.
    Creates its own transaction context.
    """
    async with async_session() as session:
        repo = AgentRepository(session)
        thought_info = await repo.create_thought_without_commit(
            agent_id=agent_id,
            step_number=step_number,
            thought_type=thought_type,
            content=content,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
        )
        await session.commit()
        return thought_info


async def update_thought_with_result_safe(thought_id: UUID, result: str) -> None:
    """
    Update a thought with a result with proper session handling.
    Creates its own transaction context.
    """
    async with async_session() as session:
        repo = AgentRepository(session)
        await repo.update_thought_with_result_without_commit(thought_id, result)
        await session.commit()
