"""Configuration settings loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class JiraSettings(BaseSettings):
    """Jira MCP server settings.

    All settings are loaded from environment variables prefixed with JIRA_.
    Environment variables are passed by the parent process (app/mcp/jira_mcp.py)
    which reads the root .env via load_dotenv().
    """

    model_config = {"env_prefix": "JIRA_"}

    # Required
    url: str
    email: str
    api_token: str

    # Optional
    read_only_mode: bool = False
    max_results: int = 50
    timeout: int = 30
    rate_limit_calls: int = 10
    rate_limit_period: int = 60
    log_level: str = "INFO"
    ssl_verify: bool | str = True
