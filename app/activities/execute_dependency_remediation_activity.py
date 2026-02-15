"""
Temporal activity for executing dependency remediation on a single repository.
"""
from typing import Any, Dict
from temporalio import activity
from pathlib import Path
import json
from datetime import datetime

from app.agents.dependency_remediation.agent import run_dependency_remediation_agent


@activity.defn(name="execute_dependency_remediation_activity")
async def execute_dependency_remediation_activity(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute dependency remediation agent for a single repository.

    This activity handles:
    - Creating vulnerability-object.json for the target repository
    - Setting up workspace directory
    - Invoking the dependency remediation agent (planner, executor, verifier)
    - Returning structured results including branch_name and commit_hash

    Note: Does NOT create PRs - that's handled by execute_pull_request_activity.

    Args:
        payload: Dictionary containing:
                {
                    "org": "AgentPOC-Org",
                    "repository": {
                        "name": "python-uv-test",
                        "html_url": "https://github.com/...",
                        "security_alerts": [...]
                    }
                }

    Returns:
        Dictionary containing results:
        {
            "status": "success" | "failure" | "partial",
            "repo_name": "python-uv-test",
            "branch_name": "fix/security-alerts-20260215-143022",
            "commit_hash": "abc123",
            "major_version_updates": ["containerd"],
            "packages_updated": [...],
            "verification_status": "verified",
            "workspace_dir": "/path/to/workspace",
            "vulnerability_data": {...},
            "duration_ms": 45000,
            "error": null | "error message",
            "total_cost_usd": 0.05,
            "num_turns": 12
        }
    """
    activity.logger.info("Starting execute_dependency_remediation_activity")

    org = payload.get("org")
    repository = payload.get("repository")

    if not org:
        raise ValueError("Missing required parameter: org")
    if not repository:
        raise ValueError("Missing required parameter: repository")

    repo_name = repository.get("name", "unknown")

    activity.logger.info(
        f"Executing dependency remediation for repository: {org}/{repo_name}"
    )

    # Create workspace directory for this execution
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    workspace_dir = Path("workspace") / f"{repo_name}_{timestamp}"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Create log directory
    log_dir = Path("logs") / f"remediation_{repo_name}_{timestamp}"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Write vulnerability-object.json for this repository
    vulnerability_object = {
        "org": org,
        "source": "github_dependabot_org_alerts",
        "state": "open",
        "repository": repository
    }

    vulnerability_file = workspace_dir / "vulnerability-object.json"
    with open(vulnerability_file, "w", encoding="utf-8") as f:
        json.dump(vulnerability_object, f, indent=2)

    activity.logger.info(
        f"Created vulnerability-object.json at {vulnerability_file}"
    )

    # Send heartbeat to indicate activity is still running
    activity.heartbeat(f"Starting dependency remediation for {repo_name}")

    try:
        # Execute the dependency remediation agent
        result = await run_dependency_remediation_agent(
            org=org,
            repository_data=repository,
            workspace_dir=workspace_dir,
            log_dir=log_dir
        )

        # Add workspace_dir and vulnerability_data to result for PR activity
        result["workspace_dir"] = str(workspace_dir)
        result["vulnerability_data"] = vulnerability_object

        activity.logger.info(
            f"Dependency remediation completed for {repo_name}: "
            f"status={result['status']}, "
            f"branch={result.get('branch_name')}, "
            f"duration={result['duration_ms']}ms"
        )

        # Send final heartbeat
        activity.heartbeat(f"Completed: {result['status']}")

        return result

    except Exception as e:
        activity.logger.error(
            f"Dependency remediation failed for {repo_name}: {str(e)}",
            exc_info=True
        )

        return {
            "status": "failure",
            "repo_name": repo_name,
            "branch_name": None,
            "commit_hash": None,
            "major_version_updates": [],
            "packages_updated": [],
            "verification_status": "not_run",
            "workspace_dir": str(workspace_dir),
            "vulnerability_data": vulnerability_object,
            "duration_ms": 0,
            "error": str(e),
            "total_cost_usd": None,
            "num_turns": 0
        }
