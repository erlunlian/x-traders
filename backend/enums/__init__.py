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


class AgentDecisionTrigger(str, Enum):
    """What triggered an agent's decision"""
    TWEET = "TWEET"  # Reacting to a tweet
    AUTONOMOUS = "AUTONOMOUS"  # Agent decided on its own
    SCHEDULED = "SCHEDULED"  # Periodic review
    MARKET_EVENT = "MARKET_EVENT"  # Price movement, trade, etc


class AgentAction(str, Enum):
    """Actions an agent can take"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    RESEARCH = "RESEARCH"
    REST = "REST"
    CONTEMPLATE = "CONTEMPLATE"
    CHECK_MARKET = "CHECK_MARKET"
    ANALYZE_TWEETS = "ANALYZE_TWEETS"


class AgentThoughtType(str, Enum):
    """Types of thoughts in agent's decision process"""
    THINKING = "THINKING"  # General thinking
    ANALYZING = "ANALYZING"  # Analyzing data
    DECIDING = "DECIDING"  # Making a decision
    EXECUTING = "EXECUTING"  # Executing action
    REFLECTING = "REFLECTING"  # Contemplating results


class AgentMemoryType(str, Enum):
    """Types of agent memory"""
    WORKING = "WORKING"  # Current working memory
    COMPRESSED = "COMPRESSED"  # Compressed older memories
    INSIGHTS = "INSIGHTS"  # Learned patterns and insights


class LLMModel(str, Enum):
    """Available LLM models for agents - values are actual API model strings"""
    # OpenAI models
    GPT_4O = "gpt-4o-2024-08-06"  # GPT-4o latest
    GPT_4O_MINI = "gpt-4o-mini-2024-07-18"  # GPT-4o mini - cost efficient
    GPT_5 = "gpt-5-2025-08-07"  # GPT-5 full model
    GPT_5_MINI = "gpt-5-mini-2025-08-07"  # GPT-5 mini version
    GPT_5_NANO = "gpt-5-nano-2025-08-07"  # GPT-5 nano - smallest and fastest
    
    # Anthropic models  
    CLAUDE_35_SONNET = "claude-3.5-sonnet-20241022"  # Claude 3.5 Sonnet
    CLAUDE_35_HAIKU = "claude-3.5-haiku-20241022"  # Claude 3.5 Haiku
    
    # xAI Grok models
    GROK_BETA = "grok-beta"  # Current beta model
    GROK_2 = "grok-2-1212"  # Grok 2


# Export all enums
__all__ = [
    "Side",
    "OrderType",
    "OrderStatus",
    "CancelReason",
    "MarketDataEventType",
    "MessageType",
    "AccountType",
    "AgentDecisionTrigger",
    "AgentAction",
    "AgentThoughtType",
    "AgentMemoryType",
    "LLMModel",
]