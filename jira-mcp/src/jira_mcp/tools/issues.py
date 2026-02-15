"""Issue management tools: create, get, update, assign, delete."""

from __future__ import annotations

from typing import Any

from jira_mcp.guards.rate_limit import rate_limit
from jira_mcp.guards.read_only import check_read_only
from jira_mcp.jira.adf import adf_to_text, text_to_adf
from jira_mcp.lifespan import get_jira_client
from jira_mcp.server import mcp


@mcp.tool()
@rate_limit
async def create_issue(
    project_key: str,
    summary: str,
    issue_type: str = "Task",
    description: str = "",
    priority: str | None = None,
    labels: list[str] | None = None,
    assignee_account_id: str | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a new Jira issue.

    Args:
        project_key: The project key (e.g. "PROJ").
        summary: Issue title/summary.
        issue_type: Issue type name (e.g. "Task", "Bug", "Story"). Defaults to "Task".
        description: Plain text description. Converted to ADF internally.
        priority: Priority name (e.g. "High", "Medium", "Low"). Optional.
        labels: List of labels to attach. Optional.
        assignee_account_id: Jira account ID of the assignee. Optional.
        extra_fields: Additional fields dict merged into the payload. Optional.

    Returns:
        Created issue data with id, key, and self URL.
    """
    check_read_only()
    client = get_jira_client()

    fields: dict[str, Any] = {
        "project": {"key": project_key},
        "summary": summary,
        "issuetype": {"name": issue_type},
    }
    if description:
        fields["description"] = text_to_adf(description)
    if priority:
        fields["priority"] = {"name": priority}
    if labels:
        fields["labels"] = labels
    if assignee_account_id:
        fields["assignee"] = {"accountId": assignee_account_id}
    if extra_fields:
        fields.update(extra_fields)

    return await client.create_issue(fields)


@mcp.tool()
@rate_limit
async def get_issue(issue_key: str) -> dict[str, Any]:
    """Get a Jira issue by its key (e.g. "PROJ-123").

    Args:
        issue_key: The issue key.

    Returns:
        Full issue data including fields, status, assignee, and description.
        The description is returned as both raw ADF and extracted plain text.
    """
    client = get_jira_client()
    issue = await client.get_issue(issue_key)

    # Add plain text description for easier consumption
    fields = issue.get("fields", {})
    if fields.get("description"):
        issue["_description_text"] = adf_to_text(fields["description"])

    return issue


@mcp.tool()
@rate_limit
async def update_issue(
    issue_key: str,
    summary: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    labels: list[str] | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> str:
    """Update fields on an existing Jira issue.

    Args:
        issue_key: The issue key (e.g. "PROJ-123").
        summary: New summary. Optional.
        description: New plain text description. Optional.
        priority: New priority name. Optional.
        labels: New labels list (replaces existing). Optional.
        extra_fields: Additional fields to set. Optional.

    Returns:
        Confirmation message.
    """
    check_read_only()
    client = get_jira_client()

    fields: dict[str, Any] = {}
    if summary is not None:
        fields["summary"] = summary
    if description is not None:
        fields["description"] = text_to_adf(description)
    if priority is not None:
        fields["priority"] = {"name": priority}
    if labels is not None:
        fields["labels"] = labels
    if extra_fields:
        fields.update(extra_fields)

    if not fields:
        return "No fields to update."

    await client.update_issue(issue_key, fields)
    return f"Issue {issue_key} updated successfully."


@mcp.tool()
@rate_limit
async def assign_issue(issue_key: str, assignee_account_id: str | None = None) -> str:
    """Assign a Jira issue to a user, or unassign it.

    Args:
        issue_key: The issue key (e.g. "PROJ-123").
        assignee_account_id: Jira account ID. Pass None or omit to unassign.

    Returns:
        Confirmation message.
    """
    check_read_only()
    client = get_jira_client()
    await client.assign_issue(issue_key, assignee_account_id)
    if assignee_account_id:
        return f"Issue {issue_key} assigned to {assignee_account_id}."
    return f"Issue {issue_key} unassigned."


@mcp.tool()
@rate_limit
async def delete_issue(issue_key: str) -> str:
    """Delete a Jira issue. This action is irreversible.

    Args:
        issue_key: The issue key (e.g. "PROJ-123").

    Returns:
        Confirmation message.
    """
    check_read_only()
    client = get_jira_client()
    await client.delete_issue(issue_key)
    return f"Issue {issue_key} deleted."
