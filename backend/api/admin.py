from fastapi import APIRouter, Depends, HTTPException

from api.auth import require_admin
from scripts.seed_agents import main as seed_agents_main
from scripts.seed_treasury import main as seed_treasury_main

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/seed/treasury")
async def seed_treasury():
    """Seed treasury trader, shares and a long-dated ask per configured ticker.

    Admin-only. Runs the same logic as the CLI script.
    """
    if seed_treasury_main is None:
        raise HTTPException(status_code=500, detail="Seeding module not available")

    try:
        await seed_treasury_main()
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Treasury seeding failed: {err}") from err

    return {"ok": True, "message": "Treasury seeded"}


@router.post("/seed/agents")
async def seed_agents(body: dict):
    """Seed agents with count provided in body: {"count": 10|50}."""
    if seed_agents_main is None:
        raise HTTPException(status_code=500, detail="Seeding module not available")

    count = int(body.get("count", 10)) if isinstance(body, dict) else 10
    if count not in (10, 50):
        raise HTTPException(status_code=400, detail="count must be 10 or 50")

    try:
        await seed_agents_main(count)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Agent seeding failed: {err}") from err

    return {"ok": True, "message": f"Seeded {count} agents"}


# Tweet data admin endpoints
try:
    from scripts.backfill.backfill_tweets import TweetBackfiller  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - optional
    TweetBackfiller = None  # type: ignore[assignment]

try:
    from database import async_session
    from services.backup_service import BackupService
except Exception:  # pragma: no cover - defensive
    BackupService = None  # type: ignore[assignment]
    async_session = None  # type: ignore[assignment]


@router.post("/tweets/backfill")
async def tweets_backfill():
    """Backfill tweets for all tickers.

    Admin-only. If force=True, refresh all; otherwise refresh if older than stale_hours.
    """
    if TweetBackfiller is None:
        raise HTTPException(status_code=500, detail="Backfill module not available")

    try:
        backfiller = TweetBackfiller(force_refresh=False, stale_hours=24)
        stats = await backfiller.backfill_all_tickers()
        return {
            "ok": True,
            "operation": stats.operation,
            "users_processed": stats.users_processed,
            "tweets_processed": stats.tweets_processed,
            "errors": stats.errors,
        }
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Backfill failed: {err}") from err


@router.post("/tweets/export")
async def tweets_export():
    """Export database tweets to JSON backup. Admin-only."""
    if BackupService is None or async_session is None:
        raise HTTPException(status_code=500, detail="Backup service unavailable")

    try:
        backup_service = BackupService()
        async with async_session() as session:  # type: ignore[misc]
            stats = await backup_service.export_from_database(session)
        return {
            "ok": bool(stats.success),
            "users_exported": stats.users_processed,
            "tweets_exported": stats.tweets_processed,
            "backup_file": str(backup_service.main_backup_file),
            "errors": stats.errors,
        }
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Export failed: {err}") from err


@router.post("/tweets/import")
async def tweets_import():
    """Import tweets from JSON backup into database."""
    if BackupService is None or async_session is None:
        raise HTTPException(status_code=500, detail="Backup service unavailable")

    backup_service = BackupService()

    try:
        async with async_session() as session:  # type: ignore[misc]
            stats = await backup_service.import_to_database(session)
        return {
            "ok": bool(stats.success),
            "users_imported": stats.users_processed,
            "tweets_imported": stats.tweets_processed,
            "errors": stats.errors,
        }
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Import failed: {err}") from err


@router.post("/tweets/sync")
async def tweets_sync():
    """Sync database to JSON backup and prune old backups. Admin-only."""
    if BackupService is None or async_session is None:
        raise HTTPException(status_code=500, detail="Backup service unavailable")

    backup_service = BackupService()
    try:
        async with async_session() as session:  # type: ignore[misc]
            stats = await backup_service.export_from_database(session)

        # Prune old timestamped backups, keep last 10
        backups = backup_service.list_backups()
        timestamped = [b for b in backups if b.name != "tweets_backup.json"]
        removed: list[str] = []
        if len(timestamped) > 10:
            old_backups = timestamped[:-10]
            for b in old_backups:
                try:
                    b.unlink()
                    removed.append(b.name)
                except Exception:
                    pass

        return {
            "ok": bool(stats.success),
            "users": stats.users_processed,
            "tweets": stats.tweets_processed,
            "removed_old_backups": removed,
            "errors": stats.errors,
        }
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Sync failed: {err}") from err
