"""Retry helper with exponential backoff for transient errors."""

from __future__ import annotations

import asyncio
import functools
import logging
from typing import Any, Callable

from jira_mcp.jira.errors import JiraAPIError

logger = logging.getLogger("jira_mcp")

# Status codes that are safe to retry
_RETRYABLE_CODES = {429, 500, 502, 503, 504}


def retry(max_attempts: int = 3, base_delay: float = 1.0) -> Callable:
    """Decorator that retries on transient Jira API errors with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts.
        base_delay: Initial delay in seconds, doubled on each retry.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return await fn(*args, **kwargs)
                except JiraAPIError as e:
                    last_error = e
                    if e.status_code not in _RETRYABLE_CODES or attempt == max_attempts - 1:
                        raise
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        "Retrying %s (attempt %d/%d) after %ss: %s",
                        fn.__name__,
                        attempt + 1,
                        max_attempts,
                        delay,
                        e,
                    )
                    await asyncio.sleep(delay)
            raise last_error  # type: ignore[misc]

        return wrapper

    return decorator
