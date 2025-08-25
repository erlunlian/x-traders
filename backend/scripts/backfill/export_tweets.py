#!/usr/bin/env python3
"""
Export script to backup database tweets to JSON
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from database import async_session
from dotenv import load_dotenv
from services.backup_service import BackupService

# Load environment variables
load_dotenv()


async def main():
    """Export all tweets from database to JSON backup"""
    print("=" * 50)
    print("Export Tweets to JSON Backup")
    print("=" * 50)

    backup_service = BackupService()

    async with async_session() as session:
        print(f"Exporting from database...")
        stats = await backup_service.export_from_database(session)

        if stats.success:
            print(f"\n✓ Export successful!")
            print(f"  Users exported: {stats.users_processed}")
            print(f"  Tweets exported: {stats.tweets_processed}")
            print(f"  Main backup: {backup_service.main_backup_file}")

            # List recent backups
            backups = backup_service.list_backups()
            if len(backups) > 1:
                print(f"\nRecent backups:")
                for backup_path in backups[-5:]:  # Show last 5
                    size_mb = backup_path.stat().st_size / (1024 * 1024)
                    print(f"  - {backup_path.name} ({size_mb:.2f} MB)")
        else:
            print(f"\n✗ Export failed!")
            for error in stats.errors:
                print(f"  Error: {error}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
