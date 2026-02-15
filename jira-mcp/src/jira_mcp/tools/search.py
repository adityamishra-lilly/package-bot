"""Search tools: JQL search and key-based lookup."""

from __future__ import annotations

from typing import Any

from jira_mcp.guards.rate_limit import rate_limit
from jira_mcp.jira.adf import adf_to_text
from jira_mcp.lifespan import get_jira_client, get_settings
from jira_mcp.server import mcp


@mcp.tool()
@rate_limit
async def search_issues(
    jql: str,
    max_results: int | None = None,
    start_at: int = 0,
) -> dict[str, Any]:
    """Search for Jira issues using JQL (Jira Query Language).

    Args:
        jql: JQL query string (e.g. 'project = PROJ AND status = "To Do"').
        max_results: Maximum number of results. Defaults to server config (50).
        start_at: Pagination offset. Defaults to 0.

    Returns:
        Search results with total count and list of matching issues.
        Each issue includes a _description_text field with plain text description.
    """
    client = get_jira_client()
    settings = get_settings()
    limit = max_results if max_results is not None else settings.max_results

    result = await client.search_issues(jql, max_results=limit, start_at=start_at)

    # Add plain text descriptions for easier consumption
    for issue in result.get("issues", []):
        desc = issue.get("fields", {}).get("description")
        if desc:
            issue["_description_text"] = adf_to_text(desc)

    return result


@mcp.tool()
@rate_limit
async def get_issue_by_key(issue_key: str) -> dict[str, Any]:
    """Get a Jira issue by its key. Alias for get_issue with a clearer name.

    Args:
        issue_key: The issue key (e.g. "PROJ-123").

    Returns:
        Full issue data with plain text description added as _description_text.
    """
    client = get_jira_client()
    issue = await client.get_issue(issue_key)

    fields = issue.get("fields", {})
    if fields.get("description"):
        issue["_description_text"] = adf_to_text(fields["description"])

    return issue
