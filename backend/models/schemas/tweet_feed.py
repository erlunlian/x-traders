"""
Tweet feed schemas for agent processing
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TweetForAgent(BaseModel):
    """Tweet with user context for agent decision-making"""

    tweet_id: str
    author_username: str
    author_name: Optional[str]
    author_followers: int
    author_following: int
    text: str
    like_count: int
    retweet_count: int
    reply_count: int
    quote_count: int
    view_count: int
    fetched_at: datetime
