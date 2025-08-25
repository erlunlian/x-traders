"""
Centralized enums to avoid circular imports
"""

from enum import Enum


class Side(str, Enum):
    """Order side - buy or sell"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Types of orders supported"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    IOC = "IOC"  # Immediate or Cancel (for market orders that shouldn't wait)


class OrderStatus(str, Enum):
    """Order lifecycle states"""
    PENDING = "PENDING"  # Not yet in book (being validated)
    PARTIAL = "PARTIAL"  # Partially filled
    FILLED = "FILLED"  # Completely filled
    CANCELLED = "CANCELLED"  # Cancelled by user or system
    EXPIRED = "EXPIRED"  # Time in force expired


class CancelReason(str, Enum):
    """Reasons why an order was cancelled"""
    USER = "USER"  # User requested cancellation
    EXPIRED = "EXPIRED"  # Time in force expired
    IOC_UNFILLED = "IOC_UNFILLED"  # IOC order couldn't fill immediately
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"  # Not enough cash/shares


class MarketDataEventType(str, Enum):
    """Types of market data events"""
    TRADE = "TRADE"
    QUOTE = "QUOTE"  # Best bid/ask update
    DEPTH = "DEPTH"  # Full order book update


class MessageType(str, Enum):
    """Engine message types"""
    NEW_ORDER = "NEW_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"


class AccountType(str, Enum):
    """Account types for ledger entries"""
    CASH = "CASH"
    SHARES = "SHARES"  # Will be prefixed with ticker, e.g., "SHARES:@elonmusk"


# Export all enums
__all__ = [
    "Side",
    "OrderType",
    "OrderStatus",
    "CancelReason",
    "MarketDataEventType",
    "MessageType",
    "AccountType",
]