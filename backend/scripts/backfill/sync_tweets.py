#!/usr/bin/env python3
"""
Sync script to synchronize database and JSON backup
- Exports current DB state to backup
- Can be scheduled with cron for regular backups
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

from database import async_session
from services.backup_service import BackupService

# Load environment variables
load_dotenv()


async def main():
    """Sync database to JSON backup"""
    print("=" * 50)
    print("Sync Database to JSON Backup")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 50)

    backup_service = BackupService()

    async with async_session() as session:
        # Export current database state
        print("Exporting database to backup...")
        stats = await backup_service.export_from_database(session)

        if stats.success:
            print("✓ Sync successful!")
            print(f"  Users: {stats.users_processed}")
            print(f"  Tweets: {stats.tweets_processed}")

            # Clean up old backups (keep last 10)
            backups = backup_service.list_backups()
            # Exclude main backup file from cleanup
            timestamped_backups = [b for b in backups if b.name != "tweets_backup.json"]

            if len(timestamped_backups) > 10:
                old_backups = timestamped_backups[:-10]
                print(f"\nCleaning up {len(old_backups)} old backups...")
                for old_backup in old_backups:
                    old_backup.unlink()
                    print(f"  Removed: {old_backup.name}")
        else:
            print("✗ Sync failed!")
            for error in stats.errors:
                print(f"  Error: {error}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
