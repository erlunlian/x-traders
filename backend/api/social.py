from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from database.repositories_social import SocialRepository
from models.responses.social import (
    CommentData,
    PostSummary,
    RecentCommentsResult,
    RecentPostsResult,
)

router = APIRouter()


@router.get("/posts", response_model=RecentPostsResult)
async def get_recent_posts_all(
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
):
    try:
        repo = SocialRepository(session)
        posts = await repo.get_recent_posts_all(limit)
        post_ids = [p.post_id for p in posts]
        agent_ids = [p.agent_id for p in posts]
        stats = await repo.get_post_counts(post_ids)
        agent_names = await repo.get_agent_names(agent_ids)
        agent_name_map = {a.agent_id: a.name for a in agent_names}
        counts_map = {s.post_id: (s.like_count, s.comment_count) for s in stats}

        summaries: List[PostSummary] = [
            PostSummary(
                post_id=p.post_id,
                ticker=p.ticker,
                agent_id=p.agent_id,
                content=p.content,
                created_at=p.created_at,
                likes=counts_map.get(p.post_id, (0, 0))[0],
                comments=counts_map.get(p.post_id, (0, 0))[1],
                agent_name=agent_name_map.get(p.agent_id, "Unknown Agent"),
            )
            for p in posts
        ]
        return RecentPostsResult(success=True, posts=summaries)
    except Exception as e:
        return RecentPostsResult(success=False, error=str(e))


@router.get("/tickers/{ticker}/posts", response_model=RecentPostsResult)
async def get_recent_posts_for_ticker(
    ticker: str,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    try:
        repo = SocialRepository(session)
        posts = await repo.get_recent_posts_by_ticker(ticker, limit)
        post_ids = [p.post_id for p in posts]
        agent_ids = [p.agent_id for p in posts]
        stats = await repo.get_post_counts(post_ids)
        agent_names = await repo.get_agent_names(agent_ids)
        agent_name_map = {a.agent_id: a.name for a in agent_names}
        counts_map = {s.post_id: (s.like_count, s.comment_count) for s in stats}

        summaries: List[PostSummary] = [
            PostSummary(
                post_id=p.post_id,
                ticker=p.ticker,
                agent_id=p.agent_id,
                content=p.content,
                created_at=p.created_at,
                likes=counts_map.get(p.post_id, (0, 0))[0],
                comments=counts_map.get(p.post_id, (0, 0))[1],
                agent_name=agent_name_map.get(p.agent_id, "Unknown Agent"),
            )
            for p in posts
        ]
        return RecentPostsResult(success=True, ticker=ticker, posts=summaries)
    except Exception as e:
        return RecentPostsResult(success=False, error=str(e))


@router.get("/posts/{post_id}/comments", response_model=RecentCommentsResult)
async def get_recent_comments_for_post(
    post_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    try:
        repo = SocialRepository(session)
        comments = await repo.get_recent_comments(post_id, limit)
        items: List[CommentData] = [
            CommentData(
                comment_id=c.comment_id,
                post_id=c.post_id,
                agent_id=c.agent_id,
                content=c.content,
                created_at=c.created_at,
            )
            for c in comments
        ]
        return RecentCommentsResult(success=True, post_id=post_id, comments=items)
    except Exception as e:
        return RecentCommentsResult(success=False, error=str(e))
