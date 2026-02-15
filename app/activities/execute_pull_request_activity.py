"""
Temporal activity for creating pull requests after dependency remediation.
"""
from typing import Any, Dict
from temporalio import activity
from pathlib import Path
from datetime import datetime

from app.agents.pull_request import run_pull_request_agent


@activity.defn(name="execute_pull_request_activity")
async def execute_pull_request_activity(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute pull request agent to create and review a PR.

    This activity is called AFTER execute_dependency_remediation_activity
    has successfully created a fix branch with committed changes.

    Args:
        payload: Dictionary containing:
                {
                    "org": "AgentPOC-Org",
                    "repo_name": "python-uv-test",
                    "branch_name": "fix/security-alerts-20260215-143022",
                    "vulnerability_data": {
                        "org": "...",
                        "repository": {...}
                    },
                    "workspace_dir": "/path/to/workspace",
                    "major_version_updates": ["containerd"],
                    "auto_review": true
                }

    Returns:
        Dictionary containing results:
        {
            "status": "success" | "failure",
            "pr_url": "https://github.com/org/repo/pull/123",
            "pr_number": 123,
            "review_status": "approved" | "changes_requested" | null,
            "duration_ms": 15000,
            "error": null | "error message",
            "total_cost_usd": 0.02
        }
    """
    activity.logger.info("Starting execute_pull_request_activity")

    org = payload.get("org")
    repo_name = payload.get("repo_name")
    branch_name = payload.get("branch_name")
    vulnerability_data = payload.get("vulnerability_data", {})
    workspace_dir_str = payload.get("workspace_dir")
    auto_review = payload.get("auto_review", True)

    if not org:
        raise ValueError("Missing required parameter: org")
    if not repo_name:
        raise ValueError("Missing required parameter: repo_name")
    if not branch_name:
        raise ValueError("Missing required parameter: branch_name")

    activity.logger.info(
        f"Creating pull request for {org}/{repo_name} from branch {branch_name}"
    )

    # Set up workspace and log directories
    if workspace_dir_str:
        workspace_dir = Path(workspace_dir_str)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        workspace_dir = Path("workspace") / f"{repo_name}_{timestamp}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path("logs") / f"pr_{repo_name}_{timestamp}"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Send heartbeat to indicate activity is still running
    activity.heartbeat(f"Creating PR for {repo_name}")

    try:
        # Execute the pull request agent
        result = await run_pull_request_agent(
            org=org,
            repo_name=repo_name,
            branch_name=branch_name,
            vulnerability_data=vulnerability_data,
            workspace_dir=workspace_dir,
            log_dir=log_dir,
            auto_review=auto_review
        )

        activity.logger.info(
            f"Pull request creation completed for {repo_name}: "
            f"status={result['status']}, "
            f"pr_url={result.get('pr_url')}, "
            f"duration={result['duration_ms']}ms"
        )

        # Send final heartbeat
        activity.heartbeat(f"Completed: {result['status']}")

        return result

    except Exception as e:
        activity.logger.error(
            f"Pull request creation failed for {repo_name}: {str(e)}",
            exc_info=True
        )

        return {
            "status": "failure",
            "pr_url": None,
            "pr_number": None,
            "review_status": None,
            "duration_ms": 0,
            "error": str(e),
            "total_cost_usd": None
        }
