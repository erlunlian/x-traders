#!/usr/bin/env python3
"""
Backfill script to fetch 100 tweets per ticker from X API
and store them in both database and JSON backup

This script is idempotent - it can be run multiple times safely.
It will skip users/tweets that already exist unless --force is used.
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

from database import async_session
from database.repositories import XDataRepository
from models.core import Ticker
from models.schemas.backup import BackupStats
from services.backup_service import BackupService
from services.x_api_client import XApiClient

# Load environment variables
load_dotenv()


class TweetBackfiller:
    """Service to backfill tweets from API"""

    def __init__(self, force_refresh: bool = False, stale_hours: int = 24):
        self.api_client = XApiClient()
        self.backup_service = BackupService()
        self.tweets_per_ticker = 100
        self.force_refresh = force_refresh
        self.stale_threshold = timedelta(hours=stale_hours)

    def _is_data_stale(self, fetched_at: datetime) -> bool:
        """Check if data is stale and needs refresh"""
        if self.force_refresh:
            return True

        # Ensure fetched_at is timezone-aware
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)

        age = datetime.now(timezone.utc) - fetched_at
        return age > self.stale_threshold

    async def backfill_all_tickers(self) -> BackupStats:
        """
        Fetch 100 tweets for each ticker and store in database.
        Idempotent - will skip users/tweets that are already fresh.

        Returns:
            BackupStats with results
        """
        stats = BackupStats(operation="backfill", started_at=datetime.now(timezone.utc))

        async with async_session() as session:
            repo = XDataRepository(session)

            # Get all tickers
            tickers = Ticker.get_all()
            print(f"Starting backfill for {len(tickers)} tickers...")
            print(
                f"Mode: {'FORCE REFRESH' if self.force_refresh else f'Update if older than {self.stale_threshold}'}"
            )
            print("")

            skipped_users = 0

            for ticker_str in tickers:
                # Remove @ prefix for API calls
                username = ticker_str.lstrip("@")
                print(f"Processing @{username}...")

                try:
                    # Check if user exists and is fresh
                    existing_user = await repo.get_user_or_none(username)

                    if existing_user and not self._is_data_stale(existing_user.fetched_at):
                        print(
                            f"  ⟳ User data is fresh (fetched {existing_user.fetched_at}), skipping..."
                        )
                        skipped_users += 1
                        stats.users_processed += 1  # Count as processed since we verified it exists
                        continue

                    # Fetch user info from API
                    print("  Fetching user info...")
                    user_info = self.api_client.get_user_info(username)
                    await repo.upsert_user_without_commit(user_info)
                    stats.users_processed += 1
                    print(f"  ✓ User info saved ({user_info.num_followers:,} followers)")

                    # Check existing tweets count
                    existing_tweets = await repo.get_tweets_by_username(username, limit=1)

                    # Only fetch tweets if we don't have enough or they're stale
                    should_fetch_tweets = (
                        self.force_refresh
                        or len(existing_tweets) == 0
                        or (existing_tweets and self._is_data_stale(existing_tweets[0].fetched_at))
                    )

                    if should_fetch_tweets:
                        print(f"  Fetching last {self.tweets_per_ticker} tweets...")
                        tweets = self.api_client.get_last_tweets(username, self.tweets_per_ticker)

                        # Store tweets (upsert handles duplicates)
                        for tweet in tweets:
                            await repo.upsert_tweet_without_commit(tweet, username)
                            stats.tweets_processed += 1

                        print(f"  ✓ {len(tweets)} tweets saved/updated")
                    else:
                        # Count existing tweets
                        existing_count = len(
                            await repo.get_tweets_by_username(
                                username, limit=self.tweets_per_ticker
                            )
                        )
                        print(f"  ⟳ Tweets are fresh ({existing_count} cached), skipping...")
                        stats.tweets_processed += existing_count

                    # Commit after each ticker to avoid losing progress
                    await session.commit()

                except Exception as e:
                    print(f"  ✗ Error: {e}")
                    stats.errors.append(f"{username}: {str(e)}")
                    await session.rollback()
                    continue

                # Small delay to avoid rate limiting
                await asyncio.sleep(1)

            print(f"\n{'='*50}")
            print("Backfill complete!")
            print(f"  Users processed: {stats.users_processed}")
            print(f"  Users skipped (fresh): {skipped_users}")
            print(f"  Tweets processed: {stats.tweets_processed}")
            if stats.errors:
                print(f"  Errors: {len(stats.errors)}")
                for error in stats.errors[:5]:  # Show first 5 errors
                    print(f"    - {error}")

            # Export to backup after successful backfill
            print("\nExporting to JSON backup...")
            export_stats = await self.backup_service.export_from_database(session)
            if export_stats.success:
                print(f"  ✓ Backup saved to {self.backup_service.main_backup_file}")
                print(f"    - {export_stats.users_processed} users")
                print(f"    - {export_stats.tweets_processed} tweets")
            else:
                print(f"  ✗ Backup failed: {export_stats.errors}")

        stats.completed_at = datetime.now(timezone.utc)
        stats.success = len(stats.errors) == 0
        return stats


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Backfill tweets from X/Twitter API")
    parser.add_argument(
        "--force", action="store_true", help="Force refresh all data even if it exists"
    )
    parser.add_argument(
        "--stale-hours",
        type=int,
        default=24,
        help="Consider data stale after this many hours (default: 24)",
    )

    args = parser.parse_args()

    print("=" * 50)
    print("X/Twitter Tweet Backfill Script")
    print("=" * 50)

    backfiller = TweetBackfiller(force_refresh=args.force, stale_hours=args.stale_hours)
    stats = await backfiller.backfill_all_tickers()

    # Exit with error code if failed
    sys.exit(0 if stats.success else 1)


if __name__ == "__main__":
    asyncio.run(main())
