"""Project tools: list and get project details."""

from __future__ import annotations

from typing import Any

from jira_mcp.guards.rate_limit import rate_limit
from jira_mcp.lifespan import get_jira_client
from jira_mcp.server import mcp


@mcp.tool()
@rate_limit
async def list_projects() -> list[dict[str, Any]]:
    """List all Jira projects accessible to the authenticated user.

    Returns:
        List of projects, each with id, key, name, and project type.
    """
    client = get_jira_client()
    return await client.list_projects()


@mcp.tool()
@rate_limit
async def get_project(project_key: str) -> dict[str, Any]:
    """Get details of a specific Jira project.

    Args:
        project_key: The project key (e.g. "PROJ").

    Returns:
        Project details including id, key, name, and type.
    """
    client = get_jira_client()
    return await client.get_project(project_key)
