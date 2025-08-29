from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class PostSummary(BaseModel):
    post_id: UUID
    ticker: str
    agent_id: UUID
    content: str
    created_at: datetime
    likes: int
    comments: int


class RecentPostsResult(BaseModel):
    success: bool
    ticker: Optional[str] = None
    posts: Optional[List[PostSummary]] = None
    error: Optional[str] = None


class CommentData(BaseModel):
    comment_id: UUID
    post_id: UUID
    agent_id: UUID
    content: str
    created_at: datetime


class RecentCommentsResult(BaseModel):
    success: bool
    post_id: Optional[UUID] = None
    comments: Optional[List[CommentData]] = None
    error: Optional[str] = None
