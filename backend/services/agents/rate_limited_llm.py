"""
Lightweight wrappers to apply provider-scoped rate limiting and retries
around LangChain chat models and runnables without mutating underlying instances.
"""

from typing import Any

from enums import ModelProvider
from services.agents.rate_limiter import call_with_limits


class RateLimitedRunnable:
    def __init__(self, provider: ModelProvider, runnable: Any):
        self._provider = provider
        self._runnable = runnable

    async def ainvoke(self, *args, **kwargs):
        return await call_with_limits(
            self._provider, lambda: self._runnable.ainvoke(*args, **kwargs)
        )

    async def astream(self, *args, **kwargs):
        return await call_with_limits(
            self._provider, lambda: self._runnable.astream(*args, **kwargs)
        )

    def __getattr__(self, name: str):  # Delegate all other attributes/methods
        return getattr(self._runnable, name)


class RateLimitedLLM:
    def __init__(self, provider: ModelProvider, llm: Any):
        self._provider = provider
        self._llm = llm

    def bind_tools(self, tools):
        runnable = self._llm.bind_tools(tools)
        return RateLimitedRunnable(self._provider, runnable)

    async def ainvoke(self, *args, **kwargs):
        return await call_with_limits(self._provider, lambda: self._llm.ainvoke(*args, **kwargs))

    async def astream(self, *args, **kwargs):
        return await call_with_limits(self._provider, lambda: self._llm.astream(*args, **kwargs))

    def __getattr__(self, name: str):  # Delegate all other attributes/methods
        return getattr(self._llm, name)
