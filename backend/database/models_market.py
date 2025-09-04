"""
Market data SQLModel database models
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import Boolean, Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel

from enums import MarketDataEventType


class MarketDataOutbox(SQLModel, table=True):
    """Transactional outbox pattern for reliable event publishing"""

    __tablename__ = "market_data_outbox"

    event_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    event_type: MarketDataEventType = Field(
        sa_column=Column(
            ENUM(MarketDataEventType, name="market_data_event_type", create_constraint=True),
            nullable=False,
        )
    )
    ticker: str = Field(sa_column=Column(String(50), nullable=False))
    payload: Dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    published: bool = Field(default=False, sa_column=Column(Boolean, default=False, index=True))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    class Config:
        arbitrary_types_allowed = True
