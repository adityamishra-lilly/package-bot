"""Sliding-window rate limiter decorator for MCP tools."""

from __future__ import annotations

import asyncio
import functools
import time
from typing import Any, Callable

from jira_mcp.jira.errors import JiraAPIError


class RateLimiter:
    """Sliding-window rate limiter."""

    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            # Remove timestamps outside the window
            self._timestamps = [t for t in self._timestamps if now - t < self.period]
            if len(self._timestamps) >= self.max_calls:
                raise JiraAPIError(
                    f"Rate limit exceeded: {self.max_calls} calls per {self.period}s. "
                    "Try again shortly.",
                    status_code=429,
                )
            self._timestamps.append(now)


# Global limiter instance, lazily initialized
_limiter: RateLimiter | None = None


def _get_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        from jira_mcp.lifespan import get_settings

        settings = get_settings()
        _limiter = RateLimiter(settings.rate_limit_calls, settings.rate_limit_period)
    return _limiter


def reset_limiter() -> None:
    """Reset the global limiter (useful for tests)."""
    global _limiter
    _limiter = None


def rate_limit(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that enforces the global rate limit before calling the function."""

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        await _get_limiter().acquire()
        return await fn(*args, **kwargs)

    return wrapper
