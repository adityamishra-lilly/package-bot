"""Guard that blocks write operations when read-only mode is enabled."""

from jira_mcp.jira.errors import JiraPermissionError
from jira_mcp.lifespan import get_settings


def check_read_only() -> None:
    """Raise JiraPermissionError if JIRA_READ_ONLY_MODE is true."""
    settings = get_settings()
    if settings.read_only_mode:
        raise JiraPermissionError(
            "Write operation blocked: JIRA_READ_ONLY_MODE is enabled."
        )
