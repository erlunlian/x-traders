"""
Service for processing webhook data from TwitterAPI.io
"""

import os
from datetime import datetime, timezone
from typing import List

from database.repositories import XDataRepository
from models.core import Ticker
from models.schemas.webhook import (
    ProcessedTweet,
    ProcessingError,
    SkippedTweet,
    WebhookPayload,
    WebhookProcessingResult,
    WebhookTweet,
)
from models.schemas.x_api import TweetInfo, UserInfo


class XWebhookService:
    """Service for processing and storing webhook tweet data"""

    def __init__(self):
        self.expected_api_key = os.getenv("TWITTER_API_KEY")
        # Get all valid usernames without @ prefix
        self.valid_usernames = {ticker.value.lstrip("@").lower() for ticker in Ticker}

    def verify_api_key(self, received_api_key: str) -> bool:
        """Verify the webhook request is from TwitterAPI.io"""
        return bool(received_api_key == self.expected_api_key)

    def is_valid_username(self, username: str) -> bool:
        """Check if username (without @) is in our tickers list"""
        return username.lower() in self.valid_usernames

    def webhook_tweet_to_model(
        self, webhook_tweet: WebhookTweet, fetched_at: datetime
    ) -> TweetInfo:
        """Convert webhook tweet format to our Tweet model"""
        return TweetInfo(
            tweet_id=webhook_tweet.id,
            text=webhook_tweet.text,
            retweet_count=webhook_tweet.retweet_count,
            reply_count=webhook_tweet.reply_count,
            like_count=webhook_tweet.like_count,
            quote_count=webhook_tweet.quote_count or 0,
            view_count=webhook_tweet.view_count or 0,
            created_at=webhook_tweet.created_at,
            bookmark_count=webhook_tweet.bookmark_count or 0,
            is_reply=webhook_tweet.is_reply or False,
            reply_to_tweet_id=webhook_tweet.in_reply_to_id,
            conversation_id=webhook_tweet.conversation_id,
            in_reply_to_username=webhook_tweet.in_reply_to_username,
            quoted_tweet_id=webhook_tweet.quoted_tweet_id,
            retweeted_tweet_id=webhook_tweet.retweeted_tweet_id,
            entities=None,  # Webhook doesn't provide entities
            fetched_at=fetched_at,
        )

    def create_user_info_from_webhook(
        self, webhook_tweet: WebhookTweet, fetched_at: datetime
    ) -> UserInfo:
        """Create minimal UserInfo from webhook data"""
        return UserInfo(
            username=webhook_tweet.author.username,
            name=webhook_tweet.author.name,
            description=None,
            location=None,
            num_followers=0,  # Webhook doesn't provide these
            num_following=0,  # Will be updated when fetched from API
            fetched_at=fetched_at,
        )

    async def process_webhook_without_commit(
        self, repo: XDataRepository, payload: WebhookPayload
    ) -> WebhookProcessingResult:
        """
        Process webhook payload and store tweets/users in database.
        Caller must manage transaction boundaries.

        Returns:
            WebhookProcessingResult with processing details
        """
        processed_tweets: List[ProcessedTweet] = []
        skipped_tweets: List[SkippedTweet] = []
        processing_errors: List[ProcessingError] = []

        fetched_at = datetime.now(timezone.utc)
        for webhook_tweet in payload.tweets:
            try:
                # Validate username is in our tickers list
                if not self.is_valid_username(webhook_tweet.author.username):
                    skipped_tweets.append(
                        SkippedTweet(
                            tweet_id=webhook_tweet.id,
                            username=webhook_tweet.author.username,
                            reason="Username not in tickers list",
                        )
                    )
                    continue

                # First ensure user exists in database
                user = await repo.get_user_or_none(webhook_tweet.author.username)
                if not user:
                    # Create minimal user record - will be enriched later
                    user_info = self.create_user_info_from_webhook(webhook_tweet, fetched_at)
                    await repo.upsert_user_without_commit(user_info)

                # Convert and store tweet
                tweet = self.webhook_tweet_to_model(webhook_tweet, fetched_at)
                await repo.upsert_tweet_without_commit(tweet, webhook_tweet.author.username)

                processed_tweets.append(
                    ProcessedTweet(
                        tweet_id=webhook_tweet.id,
                        username=webhook_tweet.author.username,
                    )
                )

            except Exception as e:
                print("ERROR", e)
                processing_errors.append(ProcessingError(tweet_id=webhook_tweet.id, error=str(e)))

        return WebhookProcessingResult(
            processed=len(processed_tweets),
            skipped=len(skipped_tweets),
            errors=len(processing_errors),
            processed_tweets=processed_tweets,
            skipped_tweets=skipped_tweets,
            processing_errors=processing_errors,
        )
