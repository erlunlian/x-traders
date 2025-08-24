"""
Exchange configuration
"""
from typing import List

from models.core import Ticker

# Tradeable tickers - X (Twitter) profiles
TICKERS: List[str] = Ticker.get_all()

# Exchange settings
INITIAL_CASH_PER_TRADER_CENTS = 100_000_000  # $1,000,000.00
MAX_AGENTS = 100
