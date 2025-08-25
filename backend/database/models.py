import os
import sys
import uuid
from datetime import datetime

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
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.core import CancelReason, MarketDataEventType, OrderStatus, OrderType, Side


class Base(DeclarativeBase):
    """Base model with common timestamp fields"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DBOrder(Base):
    __tablename__ = "orders"

    order_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trader_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    ticker = Column(String(50), nullable=False, index=True)
    side = Column(ENUM(Side, name="order_side", create_constraint=True), nullable=False)
    order_type = Column(
        ENUM(OrderType, name="order_type", create_constraint=True), nullable=False
    )
    quantity = Column(Integer, nullable=False)
    limit_price = Column(Integer, nullable=True)
    filled_quantity = Column(Integer, default=0)
    status = Column(
        ENUM(OrderStatus, name="order_status", create_constraint=True),
        nullable=False,
        index=True,
    )
    cancel_reason = Column(
        ENUM(CancelReason, name="cancel_reason", create_constraint=True), nullable=True
    )

    # Deterministic ordering - monotonic sequence per ticker for price-time priority
    sequence = Column(BIGINT, nullable=False)

    # Time fields specific to orders
    tif_seconds = Column(Integer, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_quantity_positive"),
        CheckConstraint("filled_quantity >= 0", name="check_filled_non_negative"),
        CheckConstraint("filled_quantity <= quantity", name="check_filled_le_quantity"),
        CheckConstraint(
            "limit_price IS NULL OR limit_price > 0", name="check_limit_price_positive"
        ),
        CheckConstraint("tif_seconds > 0", name="check_tif_positive"),
        # Composite indexes for order book queries
        Index("ix_orders_ticker_status_side", "ticker", "status", "side"),
        Index("ix_orders_expires_status", "expires_at", "status"),
    )


class DBTrade(Base):
    __tablename__ = "trades"

    trade_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buy_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.order_id"))
    sell_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.order_id"))
    ticker = Column(String(50), nullable=False, index=True)
    price = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    buyer_id = Column(UUID(as_uuid=True), nullable=False)
    seller_id = Column(UUID(as_uuid=True), nullable=False)

    # Maker/taker tracking
    taker_order_id = Column(UUID(as_uuid=True), nullable=False)
    maker_order_id = Column(UUID(as_uuid=True), nullable=False)

    # Use executed_at instead of created_at for trades
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    buy_order = relationship("DBOrder", foreign_keys=[buy_order_id])
    sell_order = relationship("DBOrder", foreign_keys=[sell_order_id])

    __table_args__ = (
        CheckConstraint("price > 0", name="check_trade_price_positive"),
        CheckConstraint("quantity > 0", name="check_trade_quantity_positive"),
        Index("ix_trades_ticker_time", "ticker", "executed_at"),
    )


class DBLedgerEntry(Base):
    __tablename__ = "ledger_entries"

    entry_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trade_id = Column(UUID(as_uuid=True), ForeignKey("trades.trade_id"), nullable=True)
    trader_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    account = Column(String(50), nullable=False)  # "CASH" or "SHARES:@ticker"
    debit_in_cents = Column(BIGINT, default=0)
    credit_in_cents = Column(BIGINT, default=0)
    description = Column(String(200))

    __table_args__ = (
        CheckConstraint(
            "(debit_in_cents = 0 AND credit_in_cents > 0) OR (debit_in_cents > 0 AND credit_in_cents = 0)",
            name="check_debit_credit_exclusive",
        ),
        Index("ix_ledger_trader_account_time", "trader_id", "account", "created_at"),
    )


class DBPosition(Base):
    __tablename__ = "positions"

    # Composite primary key
    trader_id = Column(UUID(as_uuid=True), primary_key=True)
    ticker = Column(String(50), primary_key=True)
    quantity = Column(Integer, default=0, nullable=False)
    avg_cost = Column(Integer, default=0)  # Cents - only updated on buys

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="check_no_negative_positions"),
    )


class DBMarketDataOutbox(Base):
    """
    Transactional outbox pattern for reliable event publishing.
    When we execute a trade, we write the trade AND this event in the same transaction.
    A separate worker publishes these to WebSocket/Redis, ensuring at-least-once delivery.
    """

    __tablename__ = "market_data_outbox"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(
        ENUM(
            MarketDataEventType, name="market_data_event_type", create_constraint=True
        ),
        nullable=False,
    )
    ticker = Column(String(50), nullable=False)
    payload = Column(JSONB, nullable=False)
    published = Column(Boolean, default=False, index=True)


class DBSequenceCounter(Base):
    """
    Per-ticker monotonic counter for deterministic order sequencing.
    Not a queue - just assigns each order a unique sequence number (1, 2, 3...)
    to ensure price-time priority in the order book.
    """

    __tablename__ = "sequence_counters"

    ticker = Column(String(50), primary_key=True)
    last_sequence = Column(BIGINT, default=0, nullable=False)


class DBTraderAccount(Base):
    __tablename__ = "trader_accounts"

    trader_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)


class DBXUser(Base):
    """Cache for X/Twitter user information"""

    __tablename__ = "x_users"

    username = Column(String(100), primary_key=True)  # Twitter handle
    name = Column(String(200), nullable=True)
    description = Column(String(1000), nullable=True)
    location = Column(String(200), nullable=True)
    num_followers = Column(Integer, default=0)
    num_following = Column(Integer, default=0)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to tweets
    tweets = relationship("DBXTweet", back_populates="author")

    __table_args__ = (
        Index("ix_x_users_fetched_at", "fetched_at"),
    )


class DBXTweet(Base):
    """Cache for X/Twitter tweet data"""

    __tablename__ = "x_tweets"

    tweet_id = Column(String(100), primary_key=True)
    author_username = Column(String(100), ForeignKey("x_users.username"), nullable=False)
    text = Column(String(5000), nullable=False)  # X allows up to 4000 chars for premium
    
    # Metrics
    retweet_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    quote_count = Column(Integer, default=0)
    view_count = Column(BIGINT, default=0)
    bookmark_count = Column(Integer, default=0)
    
    # Tweet metadata
    is_reply = Column(Boolean, default=False)
    reply_to_tweet_id = Column(String(100), nullable=True)
    conversation_id = Column(String(100), nullable=True)
    in_reply_to_username = Column(String(100), nullable=True)
    quoted_tweet_id = Column(String(100), nullable=True)
    retweeted_tweet_id = Column(String(100), nullable=True)
    
    # Entities stored as JSONB for flexibility
    entities = Column(JSONB, nullable=True)
    
    # Timestamps
    tweet_created_at = Column(String(100), nullable=False)  # Store original format from API
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    author = relationship("DBXUser", back_populates="tweets")
    
    __table_args__ = (
        Index("ix_x_tweets_author", "author_username"),
        Index("ix_x_tweets_conversation", "conversation_id"),
        Index("ix_x_tweets_fetched_at", "fetched_at"),
        Index("ix_x_tweets_tweet_created_at", "tweet_created_at"),
    )
