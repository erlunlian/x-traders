"""
Trading-related SQLModel database models
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BIGINT,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel

from enums import CancelReason, OrderStatus, OrderType, Side


class Order(SQLModel, table=True):
    """Order model"""

    __tablename__ = "orders"

    order_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    trader_id: uuid.UUID = Field(sa_column=Column(PGUUID(as_uuid=True), nullable=False, index=True))
    ticker: str = Field(sa_column=Column(String(50), nullable=False, index=True))
    side: Side = Field(
        sa_column=Column(ENUM(Side, name="order_side", create_constraint=True), nullable=False)
    )
    order_type: OrderType = Field(
        sa_column=Column(ENUM(OrderType, name="order_type", create_constraint=True), nullable=False)
    )
    quantity: int = Field(sa_column=Column(Integer, nullable=False))
    limit_price: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    filled_quantity: int = Field(default=0, sa_column=Column(Integer, default=0))
    status: OrderStatus = Field(
        sa_column=Column(
            ENUM(OrderStatus, name="order_status", create_constraint=True),
            nullable=False,
            index=True,
        )
    )
    cancel_reason: Optional[CancelReason] = Field(
        default=None,
        sa_column=Column(
            ENUM(CancelReason, name="cancel_reason", create_constraint=True), nullable=True
        ),
    )
    sequence: int = Field(sa_column=Column(Integer, nullable=False))
    tif_seconds: int = Field(default=86400, sa_column=Column(Integer, default=86400))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )

    class Config:
        arbitrary_types_allowed = True


class Trade(SQLModel, table=True):
    """Trade execution record"""

    __tablename__ = "trades"

    trade_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    buy_order_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("orders.order_id"), nullable=False)
    )
    sell_order_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("orders.order_id"), nullable=False)
    )
    ticker: str = Field(sa_column=Column(String(50), nullable=False, index=True))
    price: int = Field(sa_column=Column(Integer, nullable=False))  # in cents
    quantity: int = Field(sa_column=Column(Integer, nullable=False))
    buyer_id: uuid.UUID = Field(sa_column=Column(PGUUID(as_uuid=True), nullable=False))
    seller_id: uuid.UUID = Field(sa_column=Column(PGUUID(as_uuid=True), nullable=False))
    taker_order_id: uuid.UUID = Field(sa_column=Column(PGUUID(as_uuid=True), nullable=False))
    maker_order_id: uuid.UUID = Field(sa_column=Column(PGUUID(as_uuid=True), nullable=False))
    executed_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )

    class Config:
        arbitrary_types_allowed = True


class Position(SQLModel, table=True):
    """Position tracking"""

    __tablename__ = "positions"

    trader_id: uuid.UUID = Field(sa_column=Column(PGUUID(as_uuid=True), primary_key=True))
    ticker: str = Field(sa_column=Column(String(50), primary_key=True))
    quantity: int = Field(default=0, sa_column=Column(Integer, default=0, nullable=False))
    avg_cost: int = Field(default=0, sa_column=Column(Integer, default=0))  # Cents
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )

    __table_args__ = (CheckConstraint("quantity >= 0", name="check_no_negative_positions"),)

    class Config:
        arbitrary_types_allowed = True


class LedgerEntry(SQLModel, table=True):
    """Double-entry bookkeeping ledger"""

    __tablename__ = "ledger_entries"

    entry_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    trade_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PGUUID(as_uuid=True), ForeignKey("trades.trade_id"), nullable=True),
    )
    trader_id: uuid.UUID = Field(sa_column=Column(PGUUID(as_uuid=True), nullable=False, index=True))
    account: str = Field(sa_column=Column(String(100), nullable=False, index=True))
    debit_in_cents: int = Field(default=0, sa_column=Column(BIGINT, default=0))
    credit_in_cents: int = Field(default=0, sa_column=Column(BIGINT, default=0))
    description: str = Field(sa_column=Column(String(500), nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )

    class Config:
        arbitrary_types_allowed = True


class SequenceCounter(SQLModel, table=True):
    """Sequence counter for order IDs"""

    __tablename__ = "sequence_counters"

    ticker: str = Field(sa_column=Column(String(50), primary_key=True))
    last_sequence: int = Field(sa_column=Column(Integer, nullable=False, default=0))

    class Config:
        arbitrary_types_allowed = True


class TraderAccount(SQLModel, table=True):
    """Trader account"""

    __tablename__ = "trader_accounts"

    trader_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    is_active: bool = Field(default=True, sa_column=Column(Boolean, default=True))
    is_admin: bool = Field(default=False, sa_column=Column(Boolean, default=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )

    # Enforce at most one admin trader via a partial unique index (PostgreSQL)
    __table_args__ = (
        Index(
            "uq_single_admin",
            "is_admin",
            unique=True,
            postgresql_where=text("is_admin IS TRUE"),
        ),
    )

    class Config:
        arbitrary_types_allowed = True
