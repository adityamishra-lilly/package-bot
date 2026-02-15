"""Transition tools: get available transitions and move issues between statuses."""

from __future__ import annotations

from typing import Any

from jira_mcp.guards.rate_limit import rate_limit
from jira_mcp.guards.read_only import check_read_only
from jira_mcp.lifespan import get_jira_client
from jira_mcp.server import mcp


@mcp.tool()
@rate_limit
async def get_transitions(issue_key: str) -> list[dict[str, Any]]:
    """Get available workflow transitions for a Jira issue.

    Args:
        issue_key: The issue key (e.g. "PROJ-123").

    Returns:
        List of available transitions, each with id, name, and target status.
    """
    client = get_jira_client()
    result = await client.get_transitions(issue_key)
    return result.get("transitions", [])


@mcp.tool()
@rate_limit
async def transition_issue(
    issue_key: str,
    transition_id: str,
    fields: dict[str, Any] | None = None,
) -> str:
    """Transition a Jira issue to a new status.

    Use get_transitions first to find the available transition IDs.

    Args:
        issue_key: The issue key (e.g. "PROJ-123").
        transition_id: The transition ID (from get_transitions).
        fields: Optional fields required by the transition.

    Returns:
        Confirmation message.
    """
    check_read_only()
    client = get_jira_client()
    await client.transition_issue(issue_key, transition_id, fields)
    return f"Issue {issue_key} transitioned successfully (transition_id={transition_id})."
