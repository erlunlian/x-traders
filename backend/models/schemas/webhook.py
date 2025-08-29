"""
Webhook models for receiving tweets from TwitterAPI.io
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WebhookAuthor(BaseModel):
    """Author information in webhook payload"""

    id: str
    username: str = Field(alias="userName")
    name: str

    # Accept both alias names and ignore extra fields from provider
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class WebhookTweet(BaseModel):
    """Tweet data in webhook payload"""

    id: str
    text: str
    author: WebhookAuthor
    created_at: str = Field(alias="createdAt")
    retweet_count: int = Field(default=0, alias="retweetCount")
    reply_count: int = Field(default=0, alias="replyCount")
    like_count: int = Field(default=0, alias="likeCount")
    quote_count: Optional[int] = Field(default=0, alias="quoteCount")
    view_count: Optional[int] = Field(default=0, alias="viewCount")
    bookmark_count: Optional[int] = Field(default=0, alias="bookmarkCount")

    # Optional fields that might be in the payload
    is_reply: Optional[bool] = Field(default=False, alias="isReply")
    in_reply_to_id: Optional[str] = Field(default=None, alias="inReplyToId")
    conversation_id: Optional[str] = Field(default=None, alias="conversationId")
    in_reply_to_username: Optional[str] = Field(default=None, alias="inReplyToUsername")
    quoted_tweet_id: Optional[str] = None
    retweeted_tweet_id: Optional[str] = None

    # Accept both alias names and ignore extra fields from provider (e.g. quoted_tweet objects, media)
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class WebhookPayload(BaseModel):
    """Main webhook payload from TwitterAPI.io"""

    event_type: str
    rule_id: Optional[str] = None
    rule_tag: Optional[str] = None
    tweets: Optional[List[WebhookTweet]] = None
    timestamp: Optional[int] = None

    # Ignore extra fields like rule_value and others provider may send
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    @field_validator("event_type")
    def validate_event_type(cls, v):
        if v not in {"tweet", "test_webhook_url"}:
            raise ValueError(f"Invalid event_type: {v}, expected 'tweet'")
        return v


class ProcessedTweet(BaseModel):
    """Result of processing a single tweet"""

    tweet_id: str
    username: str


class SkippedTweet(BaseModel):
    """Tweet that was skipped during processing"""

    tweet_id: str
    username: str
    reason: str


class ProcessingError(BaseModel):
    """Error that occurred during processing"""

    tweet_id: str
    error: str


class WebhookProcessingResult(BaseModel):
    """Result of processing webhook payload"""

    processed: int
    skipped: int
    errors: int
    processed_tweets: List[ProcessedTweet]
    skipped_tweets: List[SkippedTweet]
    processing_errors: List[ProcessingError]
