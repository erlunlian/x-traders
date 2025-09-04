"""
Async rate limiting and retry utilities for LLM providers.

We enforce provider-scoped limits (Azure OpenAI, OpenAI, Anthropic, xAI)
using a token-bucket style limiter with semaphore for burst control and
simple RPS pacing. Includes exponential backoff retry for 429s and common
transient errors.
"""

import asyncio
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional

from enums import ModelProvider


@dataclass
class ProviderLimits:
    max_concurrent: int
    requests_per_second: float
    burst: int


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _defaults_for_provider(provider: ModelProvider) -> ProviderLimits:
    if provider == ModelProvider.AZURE_OPENAI:
        # Conservative defaults for S0 tier
        return ProviderLimits(
            max_concurrent=_env_int("LLM_AZURE_MAX_CONCURRENT", 2),
            requests_per_second=_env_float("LLM_AZURE_RPS", 0.5),
            burst=_env_int("LLM_AZURE_BURST", 2),
        )
    if provider == ModelProvider.OPENAI:
        return ProviderLimits(
            max_concurrent=_env_int("LLM_OPENAI_MAX_CONCURRENT", 4),
            requests_per_second=_env_float("LLM_OPENAI_RPS", 1.0),
            burst=_env_int("LLM_OPENAI_BURST", 4),
        )
    if provider == ModelProvider.ANTHROPIC:
        return ProviderLimits(
            max_concurrent=_env_int("LLM_ANTHROPIC_MAX_CONCURRENT", 3),
            requests_per_second=_env_float("LLM_ANTHROPIC_RPS", 0.8),
            burst=_env_int("LLM_ANTHROPIC_BURST", 3),
        )
    # xAI
    return ProviderLimits(
        max_concurrent=_env_int("LLM_XAI_MAX_CONCURRENT", 2),
        requests_per_second=_env_float("LLM_XAI_RPS", 0.5),
        burst=_env_int("LLM_XAI_BURST", 2),
    )


class AsyncRateLimiter:
    """Simple async rate limiter combining concurrency and RPS pacing."""

    def __init__(self, limits: ProviderLimits):
        self._limits = limits
        self._semaphore = asyncio.Semaphore(limits.max_concurrent)
        self._lock = asyncio.Lock()
        self._allowance = float(limits.burst)
        self._last_check = time.monotonic()

    async def _consume_token(self) -> None:
        # Token bucket refill
        async with self._lock:
            current = time.monotonic()
            elapsed = current - self._last_check
            self._last_check = current
            self._allowance += elapsed * self._limits.requests_per_second
            if self._allowance > self._limits.burst:
                self._allowance = float(self._limits.burst)

            # Wait until a token becomes available
            while self._allowance < 1.0:
                needed = 1.0 - self._allowance
                sleep_for = needed / max(self._limits.requests_per_second, 0.0001)
                await asyncio.sleep(min(sleep_for, 1.0))
                current2 = time.monotonic()
                elapsed2 = current2 - self._last_check
                self._last_check = current2
                self._allowance += elapsed2 * self._limits.requests_per_second
                if self._allowance > self._limits.burst:
                    self._allowance = float(self._limits.burst)

            self._allowance -= 1.0

    @asynccontextmanager
    async def throttle(self):
        await self._semaphore.acquire()
        try:
            await self._consume_token()
            yield
        finally:
            self._semaphore.release()


class ProviderLimiterRegistry:
    """Singleton-like registry of limiters per provider."""

    _limiters: Dict[ModelProvider, AsyncRateLimiter] = {}

    @classmethod
    def get_limiter(cls, provider: ModelProvider) -> AsyncRateLimiter:
        if provider not in cls._limiters:
            cls._limiters[provider] = AsyncRateLimiter(_defaults_for_provider(provider))
        return cls._limiters[provider]


async def with_retries(
    func: Callable[[], Awaitable[Any]],
    *,
    max_retries: int = _env_int("LLM_MAX_RETRIES", 5),
    base_delay: float = _env_float("LLM_RETRY_BASE_DELAY", 1.0),
    max_delay: float = _env_float("LLM_RETRY_MAX_DELAY", 15.0),
) -> Any:
    """Execute an async callable with exponential backoff on transient errors.

    Retries on HTTP 429 and common network/transient exceptions. Respects
    Retry-After header if the exception exposes one (best-effort).
    """

    attempt = 0
    while True:
        try:
            return await func()
        except Exception as e:  # noqa: BLE001 - we re-raise after checks
            retry_after: Optional[float] = None
            message = str(e).lower()

            is_rate_limited = "429" in message or "rate limit" in message
            is_transient = any(
                substr in message
                for substr in [
                    "timeout",
                    "temporarily unavailable",
                    "connection reset",
                    "server error",
                    "retry-after",
                    "too many requests",
                ]
            )

            # Azure/OpenAI SDKs rarely expose structured Retry-After here; best-effort parse
            # Example: "Please retry after 3 seconds"
            for token in message.split():
                if token.isdigit():
                    try:
                        seconds = float(token)
                        if 0 < seconds < 120:
                            retry_after = seconds
                            break
                    except Exception:
                        pass

            if not is_rate_limited and not is_transient:
                raise

            if attempt >= max_retries:
                raise

            attempt += 1
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            if retry_after is not None:
                delay = max(delay, retry_after)
            await asyncio.sleep(delay)

            # No early pause; only pause when retries are exhausted


async def call_with_limits(
    provider: ModelProvider,
    coro_factory: Callable[[], Awaitable[Any]],
) -> Any:
    """Run an async operation under provider-specific rate limits with retries."""

    limiter = ProviderLimiterRegistry.get_limiter(provider)

    async def _do_call() -> Any:
        async with limiter.throttle():
            return await coro_factory()

    return await with_retries(_do_call)
