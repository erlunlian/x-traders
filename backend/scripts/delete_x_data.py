#!/usr/bin/env python3
"""
Script to delete all X/Twitter data from database for testing
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from database import async_session
from database.models import XTweet, XUser
from sqlalchemy import delete


async def delete_all_x_data():
    """Delete all X users and tweets from database"""
    async with async_session() as session:
        # Delete all tweets first (due to foreign key)
        tweets_result = await session.execute(delete(XTweet))
        tweets_deleted = tweets_result.rowcount

        # Delete all users
        users_result = await session.execute(delete(XUser))
        users_deleted = users_result.rowcount

        await session.commit()

        print(f"✓ Deleted {tweets_deleted} tweets")
        print(f"✓ Deleted {users_deleted} users")
        return tweets_deleted, users_deleted


if __name__ == "__main__":
    print("Deleting all X/Twitter data from database...")
    tweets, users = asyncio.run(delete_all_x_data())
    print(f"\nDatabase cleared successfully!")
