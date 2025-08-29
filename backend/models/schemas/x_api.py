from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class UserInfo(BaseModel):
    """X/Twitter user information"""

    username: str
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    num_followers: int = 0
    num_following: int = 0
    fetched_at: datetime


class TweetEntities(BaseModel):
    """Entities found in a tweet (hashtags, urls, mentions, etc.)"""

    hashtags: List[Dict[str, Any]] = Field(default_factory=list)
    urls: List[Dict[str, Any]] = Field(default_factory=list)
    user_mentions: List[Dict[str, Any]] = Field(default_factory=list)
    symbols: List[Dict[str, Any]] = Field(default_factory=list)
    media: List[Dict[str, Any]] = Field(default_factory=list)
    polls: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        extra = "allow"  # Allow additional fields we might not know about


class TweetInfo(BaseModel):
    """X/Twitter tweet data"""

    tweet_id: str
    text: str
    retweet_count: int = 0
    reply_count: int = 0
    like_count: int = 0
    quote_count: int = 0
    view_count: int = 0
    created_at: str
    bookmark_count: int = 0
    is_reply: bool = False
    reply_to_tweet_id: Optional[str] = None
    conversation_id: Optional[str] = None
    in_reply_to_username: Optional[str] = None
    quoted_tweet_id: Optional[str] = None
    retweeted_tweet_id: Optional[str] = None
    entities: Optional[TweetEntities] = None

    class Config:
        extra = "allow"  # Allow extra fields from API

    @validator("entities", pre=True)
    def parse_entities(cls, v):
        """Convert dict to TweetEntities object"""
        if v and isinstance(v, dict):
            return TweetEntities(**v)
        return v

    @validator("quoted_tweet_id", pre=True, always=True)
    def extract_quoted_tweet_id(cls, v, values):
        """Extract ID from quoted_tweet object if present"""
        # If already has a value, use it
        if v is not None:
            return v
        # Check for quoted_tweet in the original data (values contains raw input)
        # Note: In Pydantic v1, we need to check the raw input differently
        return None  # Will be handled in from_api_response for now

    @validator("retweeted_tweet_id", pre=True, always=True)
    def extract_retweeted_tweet_id(cls, v, values):
        """Extract ID from retweeted_tweet object if present"""
        # If already has a value, use it
        if v is not None:
            return v
        # Will be handled in from_api_response for now
        return None

    @classmethod
    def from_api_response(cls, tweet_data: Dict[str, Any]) -> "TweetInfo":
        """Create Tweet from API response, handling nested fields and converting from camelCase"""
        print(f"      → Processing tweet ID: {tweet_data.get('id', 'UNKNOWN')}")
        print(f"        Text preview: {tweet_data.get('text', '')[:50]}...")

        # Map API camelCase fields to snake_case
        data = {
            "tweet_id": tweet_data.get("id"),
            "text": tweet_data.get("text"),
            "retweet_count": tweet_data.get("retweetCount", 0),
            "reply_count": tweet_data.get("replyCount", 0),
            "like_count": tweet_data.get("likeCount", 0),
            "quote_count": tweet_data.get("quoteCount", 0),
            "view_count": tweet_data.get("viewCount", 0),
            "created_at": tweet_data.get("createdAt"),
            "bookmark_count": tweet_data.get("bookmarkCount", 0),
            "is_reply": tweet_data.get("isReply", False),
            "reply_to_tweet_id": tweet_data.get("inReplyToId"),
            "conversation_id": tweet_data.get("conversationId"),
            "in_reply_to_username": tweet_data.get("inReplyToUsername"),
            "entities": tweet_data.get("entities"),
        }

        # Extract nested IDs from quoted/retweeted tweets
        if "quoted_tweet" in tweet_data:
            quoted_tweet = tweet_data["quoted_tweet"]
            if quoted_tweet and isinstance(quoted_tweet, dict):
                data["quoted_tweet_id"] = quoted_tweet.get("id")

        if "retweeted_tweet" in tweet_data:
            retweeted_tweet = tweet_data["retweeted_tweet"]
            if retweeted_tweet and isinstance(retweeted_tweet, dict):
                data["retweeted_tweet_id"] = retweeted_tweet.get("id")

        try:
            tweet = cls(**data)
            print(f"        ✓ Successfully created Tweet object")
            return tweet
        except Exception as e:
            print(f"        ✗ Error creating Tweet object: {e}")
            print(f"        Tweet data keys: {list(data.keys())}")
            raise
