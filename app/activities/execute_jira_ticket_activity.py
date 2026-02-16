"""
Temporal activity for creating Jira tickets after pull request creation.
"""
from typing import Any, Dict
from temporalio import activity
from pathlib import Path
from datetime import datetime

from app.agents.jira_ticket import run_jira_ticket_agent


@activity.defn(name="execute_jira_ticket_activity")
async def execute_jira_ticket_activity(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute Jira ticket agent to create and review a tracking ticket.

    This activity is called AFTER execute_pull_request_activity
    has successfully created a pull request.

    Args:
        payload: Dictionary containing:
                {
                    "org": "AgentPOC-Org",
                    "repo_name": "python-uv-test",
                    "pr_url": "https://github.com/org/repo/pull/123",
                    "pr_number": 123,
                    "branch_name": "fix/security-alerts-20260215-143022",
                    "vulnerability_data": {
                        "org": "...",
                        "repository": {...}
                    },
                    "workspace_dir": "/path/to/workspace",
                    "major_version_updates": ["containerd"],
                    "project_key": "SEC"  # optional
                }

    Returns:
        Dictionary containing results:
        {
            "status": "success" | "failure",
            "jira_key": "PROJ-456" | null,
            "jira_url": "https://team.atlassian.net/browse/PROJ-456" | null,
            "review_status": "approved" | "fixed" | "changes_requested" | null,
            "duration_ms": 15000,
            "error": null | "error message",
            "total_cost_usd": 0.02
        }
    """
    activity.logger.info("Starting execute_jira_ticket_activity")

    org = payload.get("org")
    repo_name = payload.get("repo_name")
    pr_url = payload.get("pr_url")
    pr_number = payload.get("pr_number")
    branch_name = payload.get("branch_name")
    vulnerability_data = payload.get("vulnerability_data", {})
    workspace_dir_str = payload.get("workspace_dir")
    major_version_updates = payload.get("major_version_updates", [])
    project_key = payload.get("project_key")

    if not org:
        raise ValueError("Missing required parameter: org")
    if not repo_name:
        raise ValueError("Missing required parameter: repo_name")
    if not pr_url:
        raise ValueError("Missing required parameter: pr_url")
    if not pr_number:
        raise ValueError("Missing required parameter: pr_number")

    activity.logger.info(
        f"Creating Jira ticket for {org}/{repo_name} PR #{pr_number}"
    )

    # Set up workspace and log directories
    if workspace_dir_str:
        workspace_dir = Path(workspace_dir_str)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        workspace_dir = Path("workspace") / f"{repo_name}_{timestamp}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path("logs") / f"jira_{repo_name}_{timestamp}"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Send heartbeat to indicate activity is still running
    activity.heartbeat(f"Creating Jira ticket for {repo_name}")

    try:
        # Execute the Jira ticket agent
        result = await run_jira_ticket_agent(
            org=org,
            repo_name=repo_name,
            pr_url=pr_url,
            pr_number=pr_number,
            branch_name=branch_name,
            vulnerability_data=vulnerability_data,
            workspace_dir=workspace_dir,
            log_dir=log_dir,
            major_version_updates=major_version_updates,
            project_key=project_key,
        )

        activity.logger.info(
            f"Jira ticket creation completed for {repo_name}: "
            f"status={result['status']}, "
            f"jira_key={result.get('jira_key')}, "
            f"duration={result['duration_ms']}ms"
        )

        # Send final heartbeat
        activity.heartbeat(f"Completed: {result['status']}")

        return result

    except Exception as e:
        activity.logger.error(
            f"Jira ticket creation failed for {repo_name}: {str(e)}",
            exc_info=True
        )

        return {
            "status": "failure",
            "jira_key": None,
            "jira_url": None,
            "review_status": None,
            "duration_ms": 0,
            "error": str(e),
            "total_cost_usd": None
        }
