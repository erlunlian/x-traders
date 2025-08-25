from datetime import datetime
from typing import List, Optional

from models.schemas.x_api import Tweet, UserInfo
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import DBXTweet, DBXUser


class XDataRepository:
    """
    Repository for X/Twitter data caching operations.
    Note: Methods with _in_transaction suffix do NOT commit - caller must manage transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_user_in_transaction(self, user_info: UserInfo) -> DBXUser:
        """
        Insert or update user information in cache.
        Must be called within a transaction context - does NOT commit.
        """
        stmt = (
            insert(DBXUser)
            .values(
                username=user_info.username,
                name=user_info.name,
                description=user_info.description,
                location=user_info.location,
                num_followers=user_info.num_followers,
                num_following=user_info.num_following,
                fetched_at=datetime.utcnow(),
            )
            .on_conflict_do_update(
                index_elements=["username"],
                set_={
                    "name": user_info.name,
                    "description": user_info.description,
                    "location": user_info.location,
                    "num_followers": user_info.num_followers,
                    "num_following": user_info.num_following,
                    "fetched_at": datetime.utcnow(),
                },
            )
            .returning(DBXUser)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()

    async def upsert_tweet_in_transaction(self, tweet: Tweet, author_username: str) -> DBXTweet:
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
            insert(DBXTweet)
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
                tweet_created_at=tweet.created_at,
                fetched_at=datetime.utcnow(),
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
                    "fetched_at": datetime.utcnow(),
                },
            )
            .returning(DBXTweet)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()

    async def get_user_or_none(self, username: str) -> Optional[DBXUser]:
        """Get cached user by username - returns None if not found"""
        result = await self.session.execute(
            select(DBXUser).where(DBXUser.username == username)
        )
        return result.scalar_one_or_none()

    async def get_tweet_or_none(self, tweet_id: str) -> Optional[DBXTweet]:
        """Get cached tweet by ID - returns None if not found"""
        result = await self.session.execute(
            select(DBXTweet).where(DBXTweet.tweet_id == tweet_id)
        )
        return result.scalar_one_or_none()

    async def get_tweets_by_username(
        self, username: str, limit: int = 20
    ) -> List[DBXTweet]:
        """
        Get cached tweets for a user, ordered by tweet creation time (newest first).
        
        Args:
            username: Twitter username
            limit: Maximum number of tweets to return
        """
        result = await self.session.execute(
            select(DBXTweet)
            .where(DBXTweet.author_username == username)
            .order_by(DBXTweet.tweet_created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_tweets_by_ids(self, tweet_ids: List[str]) -> List[DBXTweet]:
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
            select(DBXTweet).where(DBXTweet.tweet_id.in_(tweet_ids))
        )
        return list(result.scalars().all())

    async def bulk_upsert_tweets_in_transaction(
        self, tweets: List[Tweet], author_username: str
    ) -> List[DBXTweet]:
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

            values.append({
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
                "tweet_created_at": tweet.created_at,
                "fetched_at": datetime.utcnow(),
            })

        stmt = (
            insert(DBXTweet)
            .values(values)
            .on_conflict_do_update(
                index_elements=["tweet_id"],
                set_={
                    "text": insert(DBXTweet).excluded.text,
                    "retweet_count": insert(DBXTweet).excluded.retweet_count,
                    "reply_count": insert(DBXTweet).excluded.reply_count,
                    "like_count": insert(DBXTweet).excluded.like_count,
                    "quote_count": insert(DBXTweet).excluded.quote_count,
                    "view_count": insert(DBXTweet).excluded.view_count,
                    "bookmark_count": insert(DBXTweet).excluded.bookmark_count,
                    "is_reply": insert(DBXTweet).excluded.is_reply,
                    "reply_to_tweet_id": insert(DBXTweet).excluded.reply_to_tweet_id,
                    "conversation_id": insert(DBXTweet).excluded.conversation_id,
                    "in_reply_to_username": insert(DBXTweet).excluded.in_reply_to_username,
                    "quoted_tweet_id": insert(DBXTweet).excluded.quoted_tweet_id,
                    "retweeted_tweet_id": insert(DBXTweet).excluded.retweeted_tweet_id,
                    "entities": insert(DBXTweet).excluded.entities,
                    "fetched_at": datetime.utcnow(),
                },
            )
            .returning(DBXTweet)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return list(result.scalars().all())