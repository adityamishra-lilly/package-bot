"""
Remediation agent module - orchestrates dependency remediation and PR creation.

This module provides a unified interface for running the complete remediation workflow:
1. Dependency Remediation (planner -> executor -> verifier)
2. Pull Request Creation (creator -> reviewer)

The workflow is split into two separate agents that can be called independently:
- run_dependency_remediation_agent: Updates dependencies and commits changes
- run_pull_request_agent: Creates and reviews pull requests
- run_full_remediation: Runs both in sequence
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import logging
import json

from app.agents.dependency_remediation.agent import run_dependency_remediation_agent
from app.agents.pull_request.agent import run_pull_request_agent


async def run_full_remediation(
    org: str,
    repository_data: Dict[str, Any],
    workspace_dir: Path,
    log_dir: Path | None = None,
    create_pr: bool = True,
    auto_review: bool = True
) -> Dict[str, Any]:
    """
    Run the complete remediation workflow: dependency updates + PR creation.

    This function orchestrates:
    1. Dependency Remediation Agent (planner -> executor -> verifier)
    2. Pull Request Agent (creator -> reviewer) - if enabled

    Args:
        org: GitHub organization name
        repository_data: Repository security summary dictionary
        workspace_dir: Working directory (should contain vulnerability-object.json)
        log_dir: Optional directory for storing logs
        create_pr: Whether to create PR after remediation (default: True)
        auto_review: Whether to review PR after creation (default: True)

    Returns:
        {
            "status": "success" | "failure" | "partial",
            "repo_name": str,
            "remediation": {
                "status": str,
                "branch_name": str | None,
                "commit_hash": str | None,
                "major_version_updates": List[str],
                "packages_updated": List[Dict],
                "verification_status": str,
                "duration_ms": int
            },
            "pull_request": {
                "status": str,
                "pr_url": str | None,
                "pr_number": int | None,
                "review_status": str | None,
                "duration_ms": int
            } | None,
            "total_duration_ms": int,
            "error": None | str,
            "total_cost_usd": float | None
        }
    """
    repo_name = repository_data.get("name", "unknown")
    start_time = datetime.now()

    # Create log directory if not provided
    if log_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path("logs") / f"full_remediation_{repo_name}_{timestamp}"

    log_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "status": "failure",
        "repo_name": repo_name,
        "remediation": None,
        "pull_request": None,
        "total_duration_ms": 0,
        "error": None,
        "total_cost_usd": 0.0
    }

    try:
        # Phase 1: Dependency Remediation
        logging.info(f"Starting dependency remediation for {repo_name}")

        remediation_log_dir = log_dir / "remediation"
        remediation_result = await run_dependency_remediation_agent(
            org=org,
            repository_data=repository_data,
            workspace_dir=workspace_dir,
            log_dir=remediation_log_dir
        )

        result["remediation"] = remediation_result

        if remediation_result.get("total_cost_usd"):
            result["total_cost_usd"] += remediation_result["total_cost_usd"]

        # Check if remediation succeeded
        if remediation_result.get("status") != "success":
            result["status"] = "failure"
            result["error"] = f"Remediation failed: {remediation_result.get('error', 'Unknown error')}"
            logging.error(f"Remediation failed for {repo_name}")
            return result

        logging.info(f"Remediation completed for {repo_name}")

        # Phase 2: Pull Request Creation (if enabled)
        if create_pr and remediation_result.get("branch_name"):
            logging.info(f"Starting PR creation for {repo_name}")

            pr_log_dir = log_dir / "pull_request"
            pr_result = await run_pull_request_agent(
                org=org,
                repo_name=repo_name,
                branch_name=remediation_result["branch_name"],
                vulnerability_data=repository_data,
                workspace_dir=workspace_dir,
                log_dir=pr_log_dir,
                auto_review=auto_review
            )

            result["pull_request"] = pr_result

            if pr_result.get("total_cost_usd"):
                result["total_cost_usd"] += pr_result["total_cost_usd"]

            if pr_result.get("status") == "success":
                result["status"] = "success"
                logging.info(f"PR created for {repo_name}: {pr_result.get('pr_url')}")
            else:
                result["status"] = "partial"
                result["error"] = f"PR creation failed: {pr_result.get('error', 'Unknown error')}"
                logging.warning(f"PR creation failed for {repo_name}, but remediation succeeded")
        else:
            # Remediation only (no PR)
            result["status"] = "success"
            if not create_pr:
                logging.info(f"PR creation skipped for {repo_name} (create_pr=False)")
            else:
                logging.warning(f"No branch name from remediation for {repo_name}")

    except Exception as e:
        result["status"] = "failure"
        result["error"] = str(e)
        logging.error(f"Full remediation failed for {repo_name}: {e}", exc_info=True)

    finally:
        end_time = datetime.now()
        result["total_duration_ms"] = int((end_time - start_time).total_seconds() * 1000)

        # Write summary to log
        summary_file = log_dir / "summary.json"
        with open(summary_file, "w") as f:
            json.dump(result, f, indent=2, default=str)

        logging.info(f"Full remediation complete for {repo_name}: {result['status']}")

    return result


# Convenience exports for direct access to individual agents
__all__ = [
    "run_full_remediation",
    "run_dependency_remediation_agent",
    "run_pull_request_agent",
]
