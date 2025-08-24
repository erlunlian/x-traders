from enum import Enum


class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    IOC = "IOC"  # Immediate-or-cancel


class OrderStatus(Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class CancelReason(Enum):
    USER = "USER"
    EXPIRED = "EXPIRED"
    IOC_UNFILLED = "IOC_UNFILLED"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"


class AccountType(Enum):
    CASH = "CASH"
    SHARES = "SHARES"  # Will be prefixed with ticker, e.g., "SHARES:@elonmusk"


class MarketDataEventType(Enum):
    TRADE = "TRADE"
    QUOTE = "QUOTE"
    DEPTH = "DEPTH"
