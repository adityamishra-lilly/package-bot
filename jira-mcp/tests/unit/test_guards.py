"""Tests for read-only guard and rate limiter."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from jira_mcp.guards.rate_limit import RateLimiter, rate_limit
from jira_mcp.jira.errors import JiraAPIError, JiraPermissionError


class TestReadOnlyGuard:
    def test_blocks_when_enabled(self):
        mock_settings = type("S", (), {"read_only_mode": True})()
        with patch("jira_mcp.guards.read_only.get_settings", return_value=mock_settings):
            from jira_mcp.guards.read_only import check_read_only

            with pytest.raises(JiraPermissionError, match="READ_ONLY_MODE"):
                check_read_only()

    def test_allows_when_disabled(self):
        mock_settings = type("S", (), {"read_only_mode": False})()
        with patch("jira_mcp.guards.read_only.get_settings", return_value=mock_settings):
            from jira_mcp.guards.read_only import check_read_only

            check_read_only()  # Should not raise


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        limiter = RateLimiter(max_calls=3, period=60)
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()

    @pytest.mark.asyncio
    async def test_blocks_over_limit(self):
        limiter = RateLimiter(max_calls=2, period=60)
        await limiter.acquire()
        await limiter.acquire()
        with pytest.raises(JiraAPIError, match="Rate limit"):
            await limiter.acquire()

    @pytest.mark.asyncio
    async def test_decorator_applies_rate_limit(self):
        call_count = 0

        @rate_limit
        async def my_tool():
            nonlocal call_count
            call_count += 1
            return "ok"

        mock_limiter = RateLimiter(max_calls=100, period=60)
        with patch("jira_mcp.guards.rate_limit._get_limiter", return_value=mock_limiter):
            result = await my_tool()
            assert result == "ok"
            assert call_count == 1
