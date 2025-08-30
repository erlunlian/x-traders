#!/usr/bin/env python3
"""
Import script to restore tweets from JSON backup to database
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

from database import async_session
from services.backup_service import BackupService

# Load environment variables
load_dotenv()


async def main():
    """Import tweets from JSON backup to database"""
    parser = argparse.ArgumentParser(description="Import tweets from JSON backup")
    parser.add_argument(
        "--file",
        type=str,
        help="Specific backup file to import (default: latest backup)",
    )
    parser.add_argument("--list", action="store_true", help="List available backups and exit")

    args = parser.parse_args()

    print("=" * 50)
    print("Import Tweets from JSON Backup")
    print("=" * 50)

    backup_service = BackupService()

    # List backups if requested
    if args.list:
        backups = backup_service.list_backups()
        if backups:
            print(f"\nAvailable backups:")
            for backup_path in backups:
                size_mb = backup_path.stat().st_size / (1024 * 1024)
                modified = datetime.fromtimestamp(backup_path.stat().st_mtime)
                print(f"  {backup_path.name}")
                print(f"    Size: {size_mb:.2f} MB")
                print(f"    Modified: {modified}")
        else:
            print("No backups found!")
        return

    # Determine which backup to use
    backup_file = None
    if args.file:
        backup_file = Path(args.file)
        if not backup_file.exists():
            # Try in backup directory
            backup_file = backup_service.backup_dir / args.file
            if not backup_file.exists():
                print(f"✗ Backup file not found: {args.file}")
                sys.exit(1)

    async with async_session() as session:
        print(f"Importing from: {backup_file or 'latest backup'}")

        stats = await backup_service.import_to_database(session, backup_file)

        if stats.success:
            print("\n✓ Import successful!")
            print(f"  Users imported: {stats.users_processed}")
            print(f"  Tweets imported: {stats.tweets_processed}")
            print("\nData has been restored to the database.")
        else:
            print("\n✗ Import failed!")
            for error in stats.errors:
                print(f"  Error: {error}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
