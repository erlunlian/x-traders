from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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

    @classmethod
    def from_api_response(cls, tweet_data: Dict[str, Any]) -> "Tweet":
        """Create Tweet from API response, handling nested fields"""
        # Extract quoted tweet ID
        quoted_tweet = tweet_data.get("quoted_tweet")
        quoted_tweet_id = quoted_tweet.get("id") if quoted_tweet else None

        # Extract retweeted tweet ID
        retweeted_tweet = tweet_data.get("retweeted_tweet")
        retweeted_tweet_id = retweeted_tweet.get("id") if retweeted_tweet else None

        # Build entities if present
        entities = None
        if tweet_data.get("entities"):
            entities = TweetEntities(**tweet_data["entities"])

        return cls(
            **tweet_data,
            quoted_tweet_id=quoted_tweet_id,
            retweeted_tweet_id=retweeted_tweet_id,
            entities=entities,
        )