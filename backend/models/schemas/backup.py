"""
Backup data models for tweet export/import
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class BackupMetadata(BaseModel):
    """Metadata about the backup"""

    version: str = "1.0"
    exported_at: datetime
    ticker_count: int
    tweet_count: int
    user_count: int
    export_source: str = "database"  # "database" or "api"


class BackupUser(BaseModel):
    """User data for backup"""

    username: str
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    num_followers: int = 0
    num_following: int = 0
    fetched_at: datetime


class BackupTweet(BaseModel):
    """Tweet data for backup"""

    tweet_id: str
    author_username: str
    text: str
    retweet_count: int = 0
    reply_count: int = 0
    like_count: int = 0
    quote_count: int = 0
    view_count: int = 0
    bookmark_count: int = 0
    is_reply: bool = False
    reply_to_tweet_id: Optional[str] = None
    conversation_id: Optional[str] = None
    in_reply_to_username: Optional[str] = None
    quoted_tweet_id: Optional[str] = None
    retweeted_tweet_id: Optional[str] = None
    entities: Optional[dict] = None
    tweet_created_at: str
    fetched_at: datetime


class TweetBackup(BaseModel):
    """Complete backup structure"""

    metadata: BackupMetadata
    users: List[BackupUser]
    tweets: List[BackupTweet]


class BackupStats(BaseModel):
    """Statistics about backup operations"""

    operation: str  # "import", "export", "sync"
    started_at: datetime
    completed_at: Optional[datetime] = None
    users_processed: int = 0
    tweets_processed: int = 0
    errors: List[str] = Field(default_factory=list)
    success: bool = False
