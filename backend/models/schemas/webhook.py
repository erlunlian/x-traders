"""
Webhook models for receiving tweets from TwitterAPI.io
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class WebhookAuthor(BaseModel):
    """Author information in webhook payload"""

    id: str
    username: str
    name: str


class WebhookTweet(BaseModel):
    """Tweet data in webhook payload"""

    id: str
    text: str
    author: WebhookAuthor
    created_at: str
    retweet_count: int = Field(default=0)
    reply_count: int = Field(default=0)
    like_count: int = Field(default=0)
    quote_count: Optional[int] = Field(default=0)
    view_count: Optional[int] = Field(default=0)
    bookmark_count: Optional[int] = Field(default=0)

    # Optional fields that might be in the payload
    is_reply: Optional[bool] = Field(default=False)
    in_reply_to_id: Optional[str] = None
    conversation_id: Optional[str] = None
    in_reply_to_username: Optional[str] = None
    quoted_tweet_id: Optional[str] = None
    retweeted_tweet_id: Optional[str] = None


class WebhookPayload(BaseModel):
    """Main webhook payload from TwitterAPI.io"""

    event_type: str
    rule_id: str
    rule_tag: str
    tweets: List[WebhookTweet]
    timestamp: int

    @field_validator("event_type")
    def validate_event_type(cls, v):
        if v != "tweet":
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
