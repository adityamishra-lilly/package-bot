"""Performance timing decorator."""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable

logger = logging.getLogger("jira_mcp")


def timed(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that logs execution time of async functions."""

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        try:
            result = await fn(*args, **kwargs)
            return result
        finally:
            elapsed = time.monotonic() - start
            logger.debug("%s completed in %.3fs", fn.__name__, elapsed)

    return wrapper
