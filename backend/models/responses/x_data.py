"""
Response models for X/Twitter data tools.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class XUserInfoResult(BaseModel):
    """Result for X/Twitter user info query"""
    success: bool
    username: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    cached_at: Optional[datetime] = None
    error: Optional[str] = None


class TweetData(BaseModel):
    """Single tweet data"""
    tweet_id: str
    author: str
    text: str
    created_at: datetime
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    quotes: int = 0
    views: int = 0
    is_reply: bool = False
    cached_at: Optional[datetime] = None


class UserTweetsResult(BaseModel):
    """Result for user tweets query"""
    success: bool
    username: Optional[str] = None
    tweet_count: int = 0
    tweets: List[TweetData] = Field(default_factory=list)
    error: Optional[str] = None


class TweetsByIdsResult(BaseModel):
    """Result for tweets by IDs query"""
    success: bool
    requested: int = 0
    found: int = 0
    missing_ids: List[str] = Field(default_factory=list)
    tweets: List[TweetData] = Field(default_factory=list)
    error: Optional[str] = None


class XUserData(BaseModel):
    """Single X user data"""
    username: str
    name: str
    followers: int = 0
    following: int = 0
    cached_at: Optional[datetime] = None


class AllXUsersResult(BaseModel):
    """Result for all users query"""
    success: bool
    user_count: int = 0
    users: List[XUserData] = Field(default_factory=list)
    error: Optional[str] = None


class RecentTweetsResult(BaseModel):
    """Result for recent tweets query"""
    success: bool
    tweet_count: int = 0
    tweets: List[TweetData] = Field(default_factory=list)
    error: Optional[str] = None