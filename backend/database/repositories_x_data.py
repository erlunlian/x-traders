"""
Repository for X/Twitter data caching operations.
"""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import asc, desc, select

from database.models import XTweet, XUser
from models.schemas.tweet_feed import TweetForAgent
from models.schemas.x_api import TweetInfo, UserInfo


def parse_twitter_date(value) -> datetime:
    """Parse a date value to timezone-aware datetime.

    Supports:
    - Twitter string format: 'Wed Jun 25 22:21:48 +0000 2025'
    - ISO 8601 strings (with or without 'Z')
    - datetime instances (returned as-is)
    """
    # Already a datetime
    if isinstance(value, datetime):
        # Ensure timezone-aware; assume UTC if naive
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    # Try ISO 8601 strings
    if isinstance(value, str):
        try:
            # Handle trailing Z for UTC
            iso_str = value.replace("Z", "+00:00")
            return datetime.fromisoformat(iso_str)
        except (ValueError, TypeError):
            pass

        try:
            # Twitter format via email.utils
            return parsedate_to_datetime(value)
        except (ValueError, TypeError):
            pass

    # Fallback to current time if parsing fails
    return datetime.now(timezone.utc)


class XDataRepository:
    """
    Repository for X/Twitter data caching operations.
    Note: Methods with _in_transaction suffix do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _db_tweet_to_tweet_for_agent(self, tweet: XTweet) -> TweetForAgent:
        """Convert database tweet model to TweetForAgent schema"""
        return TweetForAgent(
            tweet_id=tweet.tweet_id,
            author_username=tweet.author_username,
            author_name=tweet.author.name if tweet.author else None,
            author_followers=tweet.author.num_followers if tweet.author else 0,
            author_following=tweet.author.num_following if tweet.author else 0,
            text=tweet.text,
            like_count=tweet.like_count,
            retweet_count=tweet.retweet_count,
            reply_count=tweet.reply_count,
            quote_count=tweet.quote_count,
            view_count=tweet.view_count,
            fetched_at=tweet.fetched_at,
        )

    def _db_user_to_user_info(self, user: XUser) -> UserInfo:
        """Convert database user model to UserInfo schema"""
        return UserInfo(
            username=user.username,
            name=user.name,
            description=user.description,
            location=user.location,
            num_followers=user.num_followers,  # type: ignore[call-arg]
            num_following=user.num_following,  # type: ignore[call-arg]
            fetched_at=user.fetched_at,
        )

    async def upsert_user_without_commit(self, user_info: UserInfo) -> UserInfo:
        """
        Insert or update user information in cache.
        Must be called within a transaction context - does NOT commit.
        """
        stmt = (
            insert(XUser)
            .values(
                username=user_info.username,
                name=user_info.name,
                description=user_info.description,
                location=user_info.location,
                num_followers=user_info.num_followers,
                num_following=user_info.num_following,
                fetched_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_update(
                index_elements=["username"],
                set_={
                    "name": user_info.name,
                    "description": user_info.description,
                    "location": user_info.location,
                    "num_followers": user_info.num_followers,
                    "num_following": user_info.num_following,
                    "fetched_at": datetime.now(timezone.utc),
                },
            )
            .returning(XUser)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        user = result.scalar_one()
        return self._db_user_to_user_info(user)

    async def upsert_tweet_without_commit(self, tweet: TweetInfo, author_username: str) -> XTweet:
        """
        Insert or update tweet in cache.
        Must be called within a transaction context - does NOT commit.

        Args:
            tweet: Tweet model from API
            author_username: Username of tweet author (must exist in x_users table)
        """
        # Convert entities to dict if present
        entities_dict = None
        if tweet.entities:
            entities_dict = tweet.entities.model_dump()

        stmt = (
            insert(XTweet)
            .values(
                tweet_id=tweet.tweet_id,
                author_username=author_username,
                text=tweet.text,
                retweet_count=tweet.retweet_count,
                reply_count=tweet.reply_count,
                like_count=tweet.like_count,
                quote_count=tweet.quote_count,
                view_count=tweet.view_count,
                bookmark_count=tweet.bookmark_count,
                is_reply=tweet.is_reply,
                reply_to_tweet_id=tweet.reply_to_tweet_id,
                conversation_id=tweet.conversation_id,
                in_reply_to_username=tweet.in_reply_to_username,
                quoted_tweet_id=tweet.quoted_tweet_id,
                retweeted_tweet_id=tweet.retweeted_tweet_id,
                entities=entities_dict,
                tweet_created_at=parse_twitter_date(tweet.created_at),
                fetched_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_update(
                index_elements=["tweet_id"],
                set_={
                    "text": tweet.text,
                    "retweet_count": tweet.retweet_count,
                    "reply_count": tweet.reply_count,
                    "like_count": tweet.like_count,
                    "quote_count": tweet.quote_count,
                    "view_count": tweet.view_count,
                    "bookmark_count": tweet.bookmark_count,
                    "is_reply": tweet.is_reply,
                    "reply_to_tweet_id": tweet.reply_to_tweet_id,
                    "conversation_id": tweet.conversation_id,
                    "in_reply_to_username": tweet.in_reply_to_username,
                    "quoted_tweet_id": tweet.quoted_tweet_id,
                    "retweeted_tweet_id": tweet.retweeted_tweet_id,
                    "entities": entities_dict,
                    "fetched_at": datetime.now(timezone.utc),
                },
            )
            .returning(XTweet)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()

    async def get_user_or_none(self, username: str) -> Optional[UserInfo]:
        """Get cached user by username - returns None if not found"""
        result = await self.session.execute(select(XUser).where(XUser.username == username))
        user = result.scalar_one_or_none()
        return self._db_user_to_user_info(user) if user else None

    async def get_tweet_or_none(self, tweet_id: str) -> Optional[XTweet]:
        """Get cached tweet by ID - returns None if not found"""
        result = await self.session.execute(select(XTweet).where(XTweet.tweet_id == tweet_id))
        return result.scalar_one_or_none()

    async def get_tweets_by_username(self, username: str, limit: int = 20) -> List[XTweet]:
        """
        Get cached tweets for a user, ordered by tweet creation time (newest first).

        Args:
            username: Twitter username
            limit: Maximum number of tweets to return
        """
        result = await self.session.execute(
            select(XTweet)
            .where(XTweet.author_username == username)
            .order_by(desc(XTweet.tweet_created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_tweets_by_ids(self, tweet_ids: List[str]) -> List[XTweet]:
        """
        Get multiple cached tweets by their IDs.

        Args:
            tweet_ids: List of tweet IDs to fetch

        Returns:
            List of cached tweets (may be fewer than requested if some aren't cached)
        """
        if not tweet_ids:
            return []

        result = await self.session.execute(
            select(XTweet).where(XTweet.tweet_id.in_(tweet_ids))  # type: ignore
        )
        return list(result.scalars().all())

    async def bulk_upsert_tweets_in_without_commit(
        self, tweets: List[TweetInfo], author_username: str
    ) -> List[XTweet]:
        """
        Bulk insert or update multiple tweets.
        More efficient than individual upserts for multiple tweets.
        Must be called within a transaction context - does NOT commit.

        Args:
            tweets: List of Tweet models from API
            author_username: Username of tweet author (must exist in x_users table)
        """
        if not tweets:
            return []

        # Prepare values for bulk insert
        values = []
        for tweet in tweets:
            entities_dict = None
            if tweet.entities:
                entities_dict = tweet.entities.model_dump()

            values.append(
                {
                    "tweet_id": tweet.tweet_id,
                    "author_username": author_username,
                    "text": tweet.text,
                    "retweet_count": tweet.retweet_count,
                    "reply_count": tweet.reply_count,
                    "like_count": tweet.like_count,
                    "quote_count": tweet.quote_count,
                    "view_count": tweet.view_count,
                    "bookmark_count": tweet.bookmark_count,
                    "is_reply": tweet.is_reply,
                    "reply_to_tweet_id": tweet.reply_to_tweet_id,
                    "conversation_id": tweet.conversation_id,
                    "in_reply_to_username": tweet.in_reply_to_username,
                    "quoted_tweet_id": tweet.quoted_tweet_id,
                    "retweeted_tweet_id": tweet.retweeted_tweet_id,
                    "entities": entities_dict,
                    "tweet_created_at": parse_twitter_date(tweet.created_at),
                    "fetched_at": datetime.now(timezone.utc),
                }
            )

        stmt = (
            insert(XTweet)
            .values(values)
            .on_conflict_do_update(
                index_elements=["tweet_id"],
                set_={
                    "text": insert(XTweet).excluded.text,
                    "retweet_count": insert(XTweet).excluded.retweet_count,
                    "reply_count": insert(XTweet).excluded.reply_count,
                    "like_count": insert(XTweet).excluded.like_count,
                    "quote_count": insert(XTweet).excluded.quote_count,
                    "view_count": insert(XTweet).excluded.view_count,
                    "bookmark_count": insert(XTweet).excluded.bookmark_count,
                    "is_reply": insert(XTweet).excluded.is_reply,
                    "reply_to_tweet_id": insert(XTweet).excluded.reply_to_tweet_id,
                    "conversation_id": insert(XTweet).excluded.conversation_id,
                    "in_reply_to_username": insert(XTweet).excluded.in_reply_to_username,
                    "quoted_tweet_id": insert(XTweet).excluded.quoted_tweet_id,
                    "retweeted_tweet_id": insert(XTweet).excluded.retweeted_tweet_id,
                    "entities": insert(XTweet).excluded.entities,
                    "fetched_at": datetime.now(timezone.utc),
                },
            )
            .returning(XTweet)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return list(result.scalars().all())

    async def get_all_users(self) -> List[UserInfo]:
        """
        Get all users from the database.

        Returns:
            List of all cached users
        """
        result = await self.session.execute(select(XUser))
        users = list(result.scalars().all())
        return [self._db_user_to_user_info(user) for user in users]

    async def get_all_tweets(self) -> List[XTweet]:
        """
        Get all tweets from the database.

        Returns:
            List of all cached tweets
        """
        result = await self.session.execute(select(XTweet).order_by(desc(XTweet.tweet_created_at)))
        return list(result.scalars().all())

    async def get_recent_tweets(self, limit: int = 20) -> List[XTweet]:
        """Get most recent tweets limited in SQL to avoid loading everything."""
        if limit <= 0:
            raise ValueError("Limit must be greater than 0")
        result = await self.session.execute(
            select(XTweet).order_by(desc(XTweet.tweet_created_at)).limit(limit)
        )
        return list(result.scalars().all())

    async def get_tweets_after_timestamp(
        self, after_timestamp: Optional[datetime], limit: int = 100
    ) -> List[XTweet]:
        """
        Get tweets newer than a given timestamp, with user data.

        Args:
            after_timestamp: Get tweets fetched after this time. If None, gets latest tweets.
            limit: Maximum number of tweets to return

        Returns:
            List of tweets with author data loaded
        """
        # Eagerly load the author relationship to avoid async lazy-loads
        query = select(XTweet).options(selectinload(XTweet.author))

        if after_timestamp:
            query = query.where(XTweet.fetched_at > after_timestamp)

        # Order by fetched_at to process in chronological order
        query = query.order_by(asc(XTweet.fetched_at)).limit(limit)

        result = await self.session.execute(query)
        tweets = list(result.scalars().all())
        return tweets

    async def get_tweets_for_agent(
        self, after_timestamp: Optional[datetime], limit: int = 100
    ) -> List[TweetForAgent]:
        """
        Get tweets as TweetForAgent models for agent processing.
        Uses mapper to convert SQLAlchemy models to Pydantic models.
        """
        tweets = await self.get_tweets_after_timestamp(after_timestamp, limit)
        return [self._db_tweet_to_tweet_for_agent(tweet) for tweet in tweets]
