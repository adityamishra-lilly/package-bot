"""Configuration settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class JiraSettings(BaseSettings):
    """Jira MCP server settings.

    All settings are loaded from environment variables prefixed with JIRA_.
    """

    model_config = {"env_prefix": "JIRA_", "env_file": ".env", "env_file_encoding": "utf-8"}

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
