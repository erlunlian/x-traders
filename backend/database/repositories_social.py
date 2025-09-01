"""
Repository for social feed operations (posts, comments, likes).
"""

from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, desc, func, select

from database.models_agents import AIAgent
from database.models_social import SocialComment, SocialLike, SocialPost
from models.schemas.agents import AgentIdName


class SocialRepository:
    """Repository for social feed models.

    Note: write methods do NOT commit. Caller manages transaction.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # Writes (used by agent tools)
    async def create_post(self, agent_id: UUID, ticker: str, content: str) -> SocialPost:
        post = SocialPost(agent_id=agent_id, ticker=ticker, content=content)
        self.session.add(post)
        await self.session.flush()
        return post

    async def add_comment(self, agent_id: UUID, post_id: UUID, content: str) -> SocialComment:
        comment = SocialComment(agent_id=agent_id, post_id=post_id, content=content)
        self.session.add(comment)
        await self.session.flush()
        return comment

    async def like_post(self, agent_id: UUID, post_id: UUID) -> Optional[SocialLike]:
        existing = await self.session.execute(
            select(SocialLike).where(
                and_(SocialLike.post_id == post_id, SocialLike.agent_id == agent_id)
            )
        )
        if existing.scalar_one_or_none():
            return None
        like = SocialLike(agent_id=agent_id, post_id=post_id)
        self.session.add(like)
        await self.session.flush()
        return like

    # Reads (used by API and tools)
    async def get_recent_posts_by_ticker(self, ticker: str, limit: int) -> List[SocialPost]:
        result = await self.session.execute(
            select(SocialPost)
            .where(SocialPost.ticker == ticker)
            .order_by(desc(SocialPost.created_at))
            .limit(limit)
        )
        return list(result.scalars())

    async def get_recent_posts_all(self, limit: int) -> List[SocialPost]:
        """Return recent posts across all tickers ordered by newest first."""
        result = await self.session.execute(
            select(SocialPost).order_by(desc(SocialPost.created_at)).limit(limit)
        )
        return list(result.scalars())

    @dataclass(frozen=True)
    class PostStats:
        post_id: UUID
        like_count: int
        comment_count: int

    async def get_post_counts(self, post_ids: List[UUID]) -> List["SocialRepository.PostStats"]:
        """Return list of PostStats for given post_ids (no dicts)."""
        if not post_ids:
            return []

        likes_q = await self.session.execute(
            select(SocialLike.post_id, func.count().label("cnt"))
            .where(SocialLike.post_id.in_(post_ids))
            .group_by(SocialLike.post_id)
        )
        comments_q = await self.session.execute(
            select(SocialComment.post_id, func.count().label("cnt"))
            .where(SocialComment.post_id.in_(post_ids))
            .group_by(SocialComment.post_id)
        )
        like_map = {row.post_id: row.cnt for row in likes_q}
        comment_map = {row.post_id: row.cnt for row in comments_q}

        return [
            SocialRepository.PostStats(
                post_id=pid, like_count=like_map.get(pid, 0), comment_count=comment_map.get(pid, 0)
            )
            for pid in post_ids
        ]

    async def get_agent_names(self, agent_ids: List[UUID]) -> List[AgentIdName]:
        """Return a list of AgentIdName schemas for given IDs."""
        if not agent_ids:
            return []
        result = await self.session.execute(
            select(AIAgent.agent_id, AIAgent.name).where(AIAgent.agent_id.in_(agent_ids))
        )
        return [AgentIdName(agent_id=row.agent_id, name=row.name) for row in result]

    async def get_recent_comments(self, post_id: UUID, limit: int) -> List[SocialComment]:
        result = await self.session.execute(
            select(SocialComment)
            .where(SocialComment.post_id == post_id)
            .order_by(desc(SocialComment.created_at))
            .limit(limit)
        )
        return list(result.scalars())
