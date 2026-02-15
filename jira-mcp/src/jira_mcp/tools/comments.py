"""Comment tools: add and retrieve comments on issues."""

from __future__ import annotations

from typing import Any

from jira_mcp.guards.rate_limit import rate_limit
from jira_mcp.guards.read_only import check_read_only
from jira_mcp.jira.adf import adf_to_text, text_to_adf
from jira_mcp.lifespan import get_jira_client
from jira_mcp.server import mcp


@mcp.tool()
@rate_limit
async def add_comment(issue_key: str, body: str) -> dict[str, Any]:
    """Add a comment to a Jira issue.

    Args:
        issue_key: The issue key (e.g. "PROJ-123").
        body: Plain text comment body. Converted to ADF internally.

    Returns:
        The created comment data.
    """
    check_read_only()
    client = get_jira_client()
    adf_body = text_to_adf(body)
    return await client.add_comment(issue_key, adf_body)


@mcp.tool()
@rate_limit
async def get_comments(issue_key: str) -> list[dict[str, Any]]:
    """Get all comments on a Jira issue.

    Args:
        issue_key: The issue key (e.g. "PROJ-123").

    Returns:
        List of comments, each with author, plain text body, and timestamps.
    """
    client = get_jira_client()
    result = await client.get_comments(issue_key)
    comments = result.get("comments", [])

    # Add plain text bodies
    for comment in comments:
        if comment.get("body"):
            comment["_body_text"] = adf_to_text(comment["body"])

    return comments
