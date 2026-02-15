"""Server lifespan: creates JiraClient on startup, closes on shutdown."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from jira_mcp.jira.client import JiraClient
from jira_mcp.logging.logger import setup_logger
from jira_mcp.settings import JiraSettings

_client: JiraClient | None = None
_settings: JiraSettings | None = None


def get_jira_client() -> JiraClient:
    """Return the active JiraClient. Only valid during server lifespan."""
    if _client is None:
        raise RuntimeError("JiraClient not initialized. Is the server running?")
    return _client


def get_settings() -> JiraSettings:
    """Return the loaded settings. Only valid during server lifespan."""
    if _settings is None:
        raise RuntimeError("Settings not loaded. Is the server running?")
    return _settings


@asynccontextmanager
async def lifespan(server) -> AsyncIterator[None]:  # noqa: ARG001
    """Async context manager that manages the JiraClient lifecycle."""
    global _client, _settings

    _settings = JiraSettings()
    logger = setup_logger(level=_settings.log_level)
    logger.info("Starting jira-mcp server (url=%s)", _settings.url)

    _client = JiraClient(
        base_url=_settings.url,
        email=_settings.email,
        api_token=_settings.api_token,
        timeout=_settings.timeout,
    )

    try:
        yield
    finally:
        logger.info("Shutting down jira-mcp server")
        await _client.close()
        _client = None
        _settings = None
