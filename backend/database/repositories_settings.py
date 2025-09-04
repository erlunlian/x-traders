from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from database.models_settings import SystemSetting


class SettingsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_value(self, key: str) -> str | None:
        result = await self.session.execute(select(SystemSetting).where(SystemSetting.key == key))
        row = result.scalar_one_or_none()
        return row.value if row else None

    async def upsert_value_without_commit(self, key: str, value: str) -> None:
        result = await self.session.execute(select(SystemSetting).where(SystemSetting.key == key))
        row = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if row:
            row.value = value
            row.updated_at = now
        else:
            row = SystemSetting(key=key, value=value, created_at=now, updated_at=now)
            self.session.add(row)
        await self.session.flush()

    async def delete_value_without_commit(self, key: str) -> None:
        result = await self.session.execute(select(SystemSetting).where(SystemSetting.key == key))
        row = result.scalar_one_or_none()
        if row:
            await self.session.delete(row)
            await self.session.flush()
