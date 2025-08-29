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
    TOOL_CALL = "TOOL_CALL"  # Tool call
    ERROR = "ERROR"  # Error


class AgentMemoryType(str, Enum):
    """Types of agent memory"""

    WORKING = "WORKING"  # Current working memory
    COMPRESSED = "COMPRESSED"  # Compressed older memories
    INSIGHTS = "INSIGHTS"  # Learned patterns and insights


class ModelProvider(str, Enum):
    """LLM providers"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    XAI = "xai"
    AZURE_OPENAI = "azure_openai"


class LLMModel(str, Enum):
    """Available LLM models for agents - values are actual API model strings"""

    # OpenAI models
    GPT_4_O = "gpt-4o-2024-08-06"  # GPT-4o latest
    GPT_4_O_MINI = "gpt-4o-mini-2024-07-18"  # GPT-4o mini - cost efficient
    GPT_5 = "gpt-5-2025-08-07"  # GPT-5 full model
    GPT_5_MINI = "gpt-5-mini-2025-08-07"  # GPT-5 mini version
    GPT_5_NANO = "gpt-5-nano-2025-08-07"  # GPT-5 nano - smallest and fastest

    # azure openai models
    GPT_4_O_AZURE = "gpt-4o"
    GPT_4_O_MINI_AZURE = "gpt-4o-mini"
    GPT_4_1_NANO_AZURE = "gpt-4.1-nano"
    GPT_5_AZURE = "gpt-5"
    GPT_5_MINI_AZURE = "gpt-5-mini"
    GPT_5_NANO_AZURE = "gpt-5-nano"

    # Anthropic models
    CLAUDE_3_5_SONNET = "claude-3.5-sonnet-20241022"  # Claude 3.5 Sonnet
    CLAUDE_3_5_HAIKU = "claude-3.5-haiku-20241022"  # Claude 3.5 Haiku

    # xAI Grok models
    GROK_BETA = "grok-beta"  # Current beta model
    GROK_2 = "grok-2-1212"  # Grok 2

    def get_provider(self) -> ModelProvider:
        """Get the provider for the model"""
        mapper = {
            self.GPT_4_O: ModelProvider.OPENAI,
            self.GPT_4_O_MINI: ModelProvider.OPENAI,
            self.GPT_5: ModelProvider.OPENAI,
            self.GPT_5_MINI: ModelProvider.OPENAI,
            self.GPT_5_NANO: ModelProvider.OPENAI,
            self.CLAUDE_3_5_SONNET: ModelProvider.ANTHROPIC,
            self.CLAUDE_3_5_HAIKU: ModelProvider.ANTHROPIC,
            self.GROK_BETA: ModelProvider.XAI,
            self.GROK_2: ModelProvider.XAI,
            self.GPT_4_O_AZURE: ModelProvider.AZURE_OPENAI,
            self.GPT_4_O_MINI_AZURE: ModelProvider.AZURE_OPENAI,
            self.GPT_4_1_NANO_AZURE: ModelProvider.AZURE_OPENAI,
            self.GPT_5_AZURE: ModelProvider.AZURE_OPENAI,
            self.GPT_5_MINI_AZURE: ModelProvider.AZURE_OPENAI,
            self.GPT_5_NANO_AZURE: ModelProvider.AZURE_OPENAI,
        }
        return mapper[self]

    def get_azure_api_version(self) -> str:
        """Get the API version for the model"""
        mapper = {
            self.GPT_4_O_MINI_AZURE: "2025-01-01-preview",
            self.GPT_5_NANO_AZURE: "2025-04-01-preview",
            self.GPT_4_1_NANO_AZURE: "2025-01-01-preview",
        }
        return mapper[self]


class AgentToolName(str, Enum):
    REST = "rest"
    BUY_LIMIT = "buy_limit"
    SELL_LIMIT = "sell_limit"
    CANCEL_ORDER = "cancel_order"
    CHECK_ORDER_STATUS = "check_order_status"
    CHECK_PORTFOLIO = "check_portfolio"
    CHECK_ORDER_BOOK = "check_order_book"
    CHECK_PRICE = "check_price"
    CHECK_ALL_PRICES = "check_all_prices"
    CHECK_RECENT_TRADES = "check_recent_trades"
    LIST_TICKERS = "list_tickers"
    GET_X_USER_INFO = "get_x_user_info"
    GET_X_USER_TWEETS = "get_x_user_tweets"
    GET_X_TWEETS_BY_IDS = "get_x_tweets_by_ids"
    GET_ALL_X_USERS = "get_all_x_users"
    GET_X_RECENT_TWEETS = "get_x_recent_tweets"


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
    "AgentToolName",
]
