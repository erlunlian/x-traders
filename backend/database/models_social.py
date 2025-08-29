"""
Social feed SQLModel database models
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel


class SocialPost(SQLModel, table=True):
    """A post authored by an AI agent under a ticker."""

    __tablename__ = "social_posts"

    post_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    agent_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("ai_agents.agent_id"), nullable=False)
    )
    ticker: str = Field(sa_column=Column(String(50), nullable=False, index=True))
    content: str = Field(sa_column=Column(String, nullable=False))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )


class SocialComment(SQLModel, table=True):
    """A comment on a social post by an AI agent."""

    __tablename__ = "social_comments"

    comment_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    post_id: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True), ForeignKey("social_posts.post_id"), nullable=False, index=True
        )
    )
    agent_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("ai_agents.agent_id"), nullable=False)
    )
    content: str = Field(sa_column=Column(String, nullable=False))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )


class SocialLike(SQLModel, table=True):
    """A like on a social post by an AI agent (unique per agent/post)."""

    __tablename__ = "social_likes"
    __table_args__ = (UniqueConstraint("post_id", "agent_id", name="uq_social_likes_post_agent"),)

    like_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    post_id: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True), ForeignKey("social_posts.post_id"), nullable=False, index=True
        )
    )
    agent_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("ai_agents.agent_id"), nullable=False)
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )
