from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class UserInfo(BaseModel):
    """X/Twitter user information"""

    username: str
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    num_followers: int = Field(default=0, alias="followers")
    num_following: int = Field(default=0, alias="following")

    class Config:
        populate_by_name = True


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


class Tweet(BaseModel):
    """X/Twitter tweet data"""

    tweet_id: str = Field(alias="id")
    text: str
    retweet_count: int = Field(default=0, alias="retweetCount")
    reply_count: int = Field(default=0, alias="replyCount")
    like_count: int = Field(default=0, alias="likeCount")
    quote_count: int = Field(default=0, alias="quoteCount")
    view_count: int = Field(default=0, alias="viewCount")
    created_at: str = Field(alias="createdAt")
    bookmark_count: int = Field(default=0, alias="bookmarkCount")
    is_reply: bool = Field(default=False, alias="isReply")
    reply_to_tweet_id: Optional[str] = Field(default=None, alias="inReplyToId")
    conversation_id: Optional[str] = Field(default=None, alias="conversationId")
    in_reply_to_username: Optional[str] = Field(default=None, alias="inReplyToUsername")
    quoted_tweet_id: Optional[str] = None
    retweeted_tweet_id: Optional[str] = None
    entities: Optional[TweetEntities] = None

    class Config:
        populate_by_name = True
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
    def from_api_response(cls, tweet_data: Dict[str, Any]) -> "Tweet":
        """Create Tweet from API response, handling nested fields"""
        print(f"      → Processing tweet ID: {tweet_data.get('id', 'UNKNOWN')}")
        print(f"        Text preview: {tweet_data.get('text', '')[:50]}...")

        # Make a copy to avoid modifying original
        data = tweet_data.copy()

        # Extract nested IDs manually since validators can't access other fields easily
        if "quoted_tweet" in data:
            quoted_tweet = data.pop("quoted_tweet")
            if quoted_tweet and isinstance(quoted_tweet, dict):
                data["quoted_tweet_id"] = quoted_tweet.get("id")

        if "retweeted_tweet" in data:
            retweeted_tweet = data.pop("retweeted_tweet")
            if retweeted_tweet and isinstance(retweeted_tweet, dict):
                data["retweeted_tweet_id"] = retweeted_tweet.get("id")

        try:
            # Now we can just pass the data directly - validator handles entities!
            tweet = cls(**data)
            print(f"        ✓ Successfully created Tweet object")
            return tweet
        except Exception as e:
            print(f"        ✗ Error creating Tweet object: {e}")
            print(f"        Tweet data keys: {list(data.keys())}")
            raise
