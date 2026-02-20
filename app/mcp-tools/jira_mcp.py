import os
from pathlib import Path
from typing import Any, Dict


def get_jira_mcp_config() -> Dict[str, Any]:
    """
    Build Jira MCP server configuration for Claude Agent SDK.

    Uses JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN from environment.

    Returns:
        MCP server configuration dict for stdio transport

    Raises:
        ValueError: If required environment variables are not set
    """
    jira_url = os.getenv("JIRA_URL")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_api_token = os.getenv("JIRA_API_TOKEN")

    if not all([jira_url, jira_email, jira_api_token]):
        raise ValueError(
            "JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN environment variables are required "
            "for Jira MCP"
        )

    # Resolve jira-mcp project directory relative to this file
    jira_mcp_dir = str(Path(__file__).resolve().parent.parent.parent / "jira-mcp")

    env = {
        "JIRA_URL": jira_url,
        "JIRA_EMAIL": jira_email,
        "JIRA_API_TOKEN": jira_api_token,
    }

    # Forward optional settings if present in the parent process environment
    for key in (
        "JIRA_SSL_VERIFY",
        "JIRA_READ_ONLY_MODE",
        "JIRA_TIMEOUT",
        "JIRA_MAX_RESULTS",
        "JIRA_RATE_LIMIT_CALLS",
        "JIRA_RATE_LIMIT_PERIOD",
        "JIRA_LOG_LEVEL",
    ):
        val = os.getenv(key)
        if val is not None:
            env[key] = val

    return {
        "command": "poetry",
        "args": ["run", "python", "-m", "jira_mcp"],
        "env": env,
        "cwd": jira_mcp_dir,
    }


def get_jira_mcp_tools() -> list[str]:
    """
    Get list of Jira MCP tool names for allowlist.

    Returns:
        List of tool names prefixed with 'mcp__jira__'
    """
    return [
        "mcp__jira__create_issue",
        "mcp__jira__get_issue",
        "mcp__jira__update_issue",
        "mcp__jira__assign_issue",
        "mcp__jira__delete_issue",
        "mcp__jira__search_issues",
        "mcp__jira__get_issue_by_key",
        "mcp__jira__add_comment",
        "mcp__jira__get_comments",
        "mcp__jira__get_transitions",
        "mcp__jira__transition_issue",
        "mcp__jira__list_projects",
        "mcp__jira__get_project",
    ]
