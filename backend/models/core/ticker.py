"""
Ticker enum for tradeable X (Twitter) profiles
"""

from enum import Enum


class Ticker(str, Enum):
    """
    Tradeable tickers - X (Twitter) profiles.
    Using str enum for easy serialization and comparison.
    """

    ELON_MUSK = "@elonmusk"
    SAM_ALTMAN = "@sama"

    @classmethod
    def get_all(cls) -> list[str]:
        """Get all ticker values as strings"""
        return [ticker.value for ticker in cls]

    @classmethod
    def is_valid(cls, ticker: str) -> bool:
        """Check if a ticker string is valid"""
        return ticker in cls._value2member_map_

    @classmethod
    def validate_or_raise(cls, ticker: str) -> None:
        """Validate ticker or raise ValueError"""
        if ticker not in cls._value2member_map_:
            raise ValueError(f"Invalid ticker: {ticker}")
