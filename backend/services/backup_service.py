"""
Service for backing up and restoring tweet data
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import XDataRepository
from models.schemas.backup import (
    BackupMetadata,
    BackupStats,
    BackupTweet,
    BackupUser,
    TweetBackup,
)
from models.schemas.x_api import TweetInfo, UserInfo


class BackupService:
    """Service for managing tweet data backups"""

    def __init__(self, backup_dir: Optional[str] = None):
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            # Default to scripts/data/tweet_backups
            self.backup_dir = (
                Path(__file__).parent.parent / "scripts" / "data" / "tweet_backups"
            )

        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.main_backup_file = self.backup_dir / "tweets_backup.json"

    def _get_timestamped_backup_path(self) -> Path:
        """Generate a timestamped backup filename"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return self.backup_dir / f"tweets_backup_{timestamp}.json"

    async def export_from_database(self, session: AsyncSession) -> BackupStats:
        """
        Export all tweets and users from database to JSON backup.
        This method only reads data, no commits needed.

        Returns:
            BackupStats with export results
        """
        stats = BackupStats(operation="export", started_at=datetime.now(timezone.utc))

        try:
            repo = XDataRepository(session)

            # Fetch all users using repository
            db_users = await repo.get_all_users()

            backup_users = []
            current_time = datetime.now(timezone.utc)
            for user in db_users:
                backup_users.append(
                    BackupUser(
                        username=user.username,
                        name=user.name,
                        description=user.description,
                        location=user.location,
                        num_followers=user.num_followers,
                        num_following=user.num_following,
                        fetched_at=current_time,  # Use export time since UserInfo doesn't have fetched_at
                    )
                )
            stats.users_processed = len(backup_users)

            # Fetch all tweets using repository
            db_tweets = await repo.get_all_tweets()

            backup_tweets = []
            for tweet in db_tweets:
                backup_tweets.append(
                    BackupTweet(
                        tweet_id=tweet.tweet_id,
                        author_username=tweet.author_username,
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
                        entities=tweet.entities,
                        tweet_created_at=tweet.tweet_created_at,
                        fetched_at=tweet.fetched_at,
                    )
                )
            stats.tweets_processed = len(backup_tweets)

            # Create backup object
            backup = TweetBackup(
                metadata=BackupMetadata(
                    exported_at=datetime.now(timezone.utc),
                    ticker_count=len(backup_users),
                    tweet_count=len(backup_tweets),
                    user_count=len(backup_users),
                    export_source="database",
                ),
                users=backup_users,
                tweets=backup_tweets,
            )

            # Save to both main and timestamped files
            self._save_backup(backup, self.main_backup_file)
            self._save_backup(backup, self._get_timestamped_backup_path())

            stats.completed_at = datetime.now(timezone.utc)
            stats.success = True

        except Exception as e:
            stats.errors.append(str(e))
            stats.success = False

        return stats

    async def import_to_database(
        self, session: AsyncSession, backup_file: Optional[Path] = None
    ) -> BackupStats:
        """
        Import tweets and users from JSON backup to database.
        This method handles the complete transaction including commit.

        Args:
            session: Database session
            backup_file: Optional specific backup file to import from

        Returns:
            BackupStats with import results
        """
        stats = BackupStats(operation="import", started_at=datetime.now(timezone.utc))

        try:
            # Load backup
            backup_path = backup_file or self.main_backup_file
            if not backup_path.exists():
                stats.errors.append(f"Backup file not found: {backup_path}")
                return stats

            backup = self._load_backup(backup_path)

            # Create repository with session
            repo = XDataRepository(session)

            # Import users
            for backup_user in backup.users:
                user_info = UserInfo(
                    username=backup_user.username,
                    name=backup_user.name or "",
                    description=backup_user.description,
                    location=backup_user.location,
                    num_followers=backup_user.num_followers,
                    num_following=backup_user.num_following,
                )
                await repo.upsert_user_without_commit(user_info)
                stats.users_processed += 1

            # Import tweets
            for backup_tweet in backup.tweets:
                tweet = TweetInfo(
                    tweet_id=backup_tweet.tweet_id,
                    text=backup_tweet.text,
                    retweet_count=backup_tweet.retweet_count,
                    reply_count=backup_tweet.reply_count,
                    like_count=backup_tweet.like_count,
                    quote_count=backup_tweet.quote_count,
                    view_count=backup_tweet.view_count,
                    created_at=backup_tweet.tweet_created_at,
                    bookmark_count=backup_tweet.bookmark_count,
                    is_reply=backup_tweet.is_reply,
                    reply_to_tweet_id=backup_tweet.reply_to_tweet_id,
                    conversation_id=backup_tweet.conversation_id,
                    in_reply_to_username=backup_tweet.in_reply_to_username,
                    quoted_tweet_id=backup_tweet.quoted_tweet_id,
                    retweeted_tweet_id=backup_tweet.retweeted_tweet_id,
                    entities=None,  # Will handle entities separately if needed
                )
                await repo.upsert_tweet_without_commit(
                    tweet, backup_tweet.author_username
                )
                stats.tweets_processed += 1

            # Commit all changes
            await session.commit()

            stats.completed_at = datetime.now(timezone.utc)
            stats.success = True

        except Exception as e:
            # Rollback on error
            await session.rollback()
            stats.errors.append(str(e))
            stats.success = False

        return stats

    def _save_backup(self, backup: TweetBackup, filepath: Path) -> None:
        """Save backup to JSON file"""
        with open(filepath, "w", encoding="utf-8") as f:
            # Convert to dict with proper datetime serialization
            backup_dict = backup.model_dump(mode="json")
            json.dump(backup_dict, f, indent=2, default=str)

    def _load_backup(self, filepath: Path) -> TweetBackup:
        """Load backup from JSON file"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Convert string dates to datetime for tweets if needed
            if "tweets" in data:
                for tweet in data["tweets"]:
                    if "tweet_created_at" in tweet and isinstance(tweet["tweet_created_at"], str):
                        # Parse Twitter date format or ISO format
                        from email.utils import parsedate_to_datetime
                        try:
                            tweet["tweet_created_at"] = parsedate_to_datetime(tweet["tweet_created_at"])
                        except (ValueError, TypeError):
                            # Try ISO format as fallback
                            try:
                                tweet["tweet_created_at"] = datetime.fromisoformat(tweet["tweet_created_at"].replace("Z", "+00:00"))
                            except (ValueError, TypeError):
                                # Use current time as last resort
                                tweet["tweet_created_at"] = datetime.now(timezone.utc)
            return TweetBackup(**data)

    def get_latest_backup(self) -> Optional[TweetBackup]:
        """Get the latest backup if it exists"""
        if self.main_backup_file.exists():
            return self._load_backup(self.main_backup_file)
        return None

    def list_backups(self) -> List[Path]:
        """List all available backup files"""
        return sorted(self.backup_dir.glob("tweets_backup*.json"))

    async def merge_api_data_to_backup(
        self, users: List[UserInfo], tweets: List[TweetInfo]
    ) -> TweetBackup:
        """
        Merge API data into existing backup or create new one

        Args:
            users: List of users from API
            tweets: List of tweets from API

        Returns:
            Updated backup
        """
        # Load existing backup or create new one
        existing = self.get_latest_backup()

        if existing:
            # Convert to dicts for merging
            existing_users = {u.username: u for u in existing.users}
            existing_tweets = {t.tweet_id: t for t in existing.tweets}

            # Merge users
            for user in users:
                existing_users[user.username] = BackupUser(
                    username=user.username,
                    name=user.name,
                    description=user.description,
                    location=user.location,
                    num_followers=user.num_followers,
                    num_following=user.num_following,
                    fetched_at=datetime.now(timezone.utc),
                )

            # Merge tweets
            for tweet in tweets:
                # Find author username (should be in users)
                author_username = None
                for user in users:
                    if user.username in tweet.tweet_id:  # Simple heuristic
                        author_username = user.username
                        break

                if author_username:
                    existing_tweets[tweet.tweet_id] = BackupTweet(
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
                        entities=None,
                        tweet_created_at=tweet.created_at,
                        fetched_at=datetime.now(timezone.utc),
                    )

            backup_users = list(existing_users.values())
            backup_tweets = list(existing_tweets.values())
        else:
            # Create new backup from API data
            backup_users = [
                BackupUser(
                    username=user.username,
                    name=user.name,
                    description=user.description,
                    location=user.location,
                    num_followers=user.num_followers,
                    num_following=user.num_following,
                    fetched_at=datetime.now(timezone.utc),
                )
                for user in users
            ]

            backup_tweets = []
            # Need to handle tweet author association properly
            # This is simplified - in real use, tweets should come with author info

        # Create new backup object
        backup = TweetBackup(
            metadata=BackupMetadata(
                exported_at=datetime.now(timezone.utc),
                ticker_count=len(backup_users),
                tweet_count=len(backup_tweets),
                user_count=len(backup_users),
                export_source="api",
            ),
            users=backup_users,
            tweets=backup_tweets,
        )

        # Save backup
        self._save_backup(backup, self.main_backup_file)
        self._save_backup(backup, self._get_timestamped_backup_path())

        return backup
