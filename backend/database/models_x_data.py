"""
X/Twitter data SQLModel database models
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import BIGINT, Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel


class XUser(SQLModel, table=True):
    """Cache for X/Twitter user data"""

    __tablename__ = "x_users"

    username: str = Field(sa_column=Column(String(100), primary_key=True))
    name: str = Field(sa_column=Column(String(100), nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(String(500), nullable=True))
    location: Optional[str] = Field(default=None, sa_column=Column(String(200), nullable=True))
    num_followers: int = Field(default=0, sa_column=Column(Integer, default=0))
    num_following: int = Field(default=0, sa_column=Column(Integer, default=0))
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )

    # Relationships
    tweets: List["XTweet"] = Relationship(back_populates="author")

    class Config:
        arbitrary_types_allowed = True


class XTweet(SQLModel, table=True):
    """Cache for X/Twitter tweet data"""

    __tablename__ = "x_tweets"

    tweet_id: str = Field(sa_column=Column(String(100), primary_key=True))
    author_username: str = Field(
        sa_column=Column(String(100), ForeignKey("x_users.username"), nullable=False)
    )
    text: str = Field(sa_column=Column(String(5000), nullable=False))

    # Metrics
    retweet_count: int = Field(default=0, sa_column=Column(Integer, default=0))
    reply_count: int = Field(default=0, sa_column=Column(Integer, default=0))
    like_count: int = Field(default=0, sa_column=Column(Integer, default=0))
    quote_count: int = Field(default=0, sa_column=Column(Integer, default=0))
    view_count: int = Field(default=0, sa_column=Column(BIGINT, default=0))
    bookmark_count: int = Field(default=0, sa_column=Column(Integer, default=0))

    # Tweet metadata
    is_reply: bool = Field(default=False, sa_column=Column(Boolean, default=False))
    reply_to_tweet_id: Optional[str] = Field(
        default=None, sa_column=Column(String(100), nullable=True)
    )
    conversation_id: Optional[str] = Field(
        default=None, sa_column=Column(String(100), nullable=True)
    )
    in_reply_to_username: Optional[str] = Field(
        default=None, sa_column=Column(String(100), nullable=True)
    )
    quoted_tweet_id: Optional[str] = Field(
        default=None, sa_column=Column(String(100), nullable=True)
    )
    retweeted_tweet_id: Optional[str] = Field(
        default=None, sa_column=Column(String(100), nullable=True)
    )

    # Entities stored as JSONB
    entities: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB, nullable=True))

    # Timestamps
    tweet_created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )

    # Relationship
    author: Optional[XUser] = Relationship(back_populates="tweets")

    class Config:
        arbitrary_types_allowed = True
