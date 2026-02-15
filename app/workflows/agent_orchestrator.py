"""
Remediation orchestrator workflow for processing multiple repositories.

This workflow orchestrates two separate activities per repository:
1. execute_dependency_remediation_activity - Updates dependencies, creates branch
2. execute_pull_request_activity - Creates and reviews PR from the fix branch
"""
from datetime import timedelta
from typing import Any, Dict, List
from temporalio import workflow
from temporalio.common import RetryPolicy

# Retry policy for dependency remediation activity (3 attempts, 15 min timeout)
DEPENDENCY_REMEDIATION_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    maximum_interval=timedelta(minutes=1),
    maximum_attempts=3,
)

# Retry policy for pull request activity (2 attempts, 5 min timeout)
PULL_REQUEST_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=2,
)

@workflow.defn
class RemediationOrchestratorWorkflow:
    """
    Orchestrator workflow for executing agent remediation across multiple repositories.
    
    This workflow:
    1. Receives a remediation plan with multiple repositories
    2. Executes agent remediation for each repository sequentially
    3. Tracks success/failure per repository
    4. Returns aggregated results
    """

    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute remediation for all repositories in the plan.

        For each repository, executes two activities in sequence:
        1. execute_dependency_remediation_activity - Updates dependencies
        2. execute_pull_request_activity - Creates PR from fix branch

        Args:
            input_data: Dictionary containing:
                {
                    "org": "AgentPOC-Org",
                    "remediation_plan_path": "dependabot-remediation-plan/remediation-plan.json",
                    "repositories": [
                        {
                            "name": "python-uv-test",
                            "html_url": "...",
                            "security_alerts": [...]
                        },
                        ...
                    ],
                    "skip_repos": [],  # optional
                    "auto_review": true  # optional, default true
                }

        Returns:
            Dictionary containing:
            {
                "status": "success" | "partial" | "failure",
                "total_repos": 5,
                "successful_repos": 3,
                "failed_repos": 2,
                "results": [
                    {
                        "repo_name": "python-uv-test",
                        "status": "success",
                        "pr_url": "https://github.com/.../pull/123",
                        "pr_number": 123,
                        "branch_name": "fix/security-alerts-...",
                        "major_version_updates": [...],
                        "remediation_duration_ms": 45000,
                        "pr_duration_ms": 15000,
                        "error": null
                    },
                    ...
                ]
            }
        """

        workflow.logger.info(
            f"Starting RemediationOrchestratorWorkflow with input: {input_data}"
        )

        org = input_data.get("org")
        repositories = input_data.get("repositories", [])
        skip_repos = input_data.get("skip_repos", [])
        auto_review = input_data.get("auto_review", True)

        if not org:
            raise ValueError("Missing required parameter: org")

        workflow.logger.info(
            f"Processing {len(repositories)} repositories for org: {org}"
        )

        results = {
            "status": "success",
            "org": org,
            "total_repos": len(repositories),
            "successful_repos": 0,
            "failed_repos": 0,
            "skipped_repos": 0,
            "results": []
        }

        # Process each repository sequentially
        for idx, repository in enumerate(repositories, 1):
            repo_name = repository.get("name", "unknown")

            # Check if repository should be skipped
            if repo_name in skip_repos:
                workflow.logger.info(
                    f"[{idx}/{len(repositories)}] Skipping repository: {repo_name}"
                )
                results["skipped_repos"] += 1
                results["results"].append({
                    "repo_name": repo_name,
                    "status": "skipped",
                    "pr_url": None,
                    "pr_number": None,
                    "branch_name": None,
                    "major_version_updates": [],
                    "remediation_duration_ms": 0,
                    "pr_duration_ms": 0,
                    "error": "Repository in skip list"
                })
                continue

            workflow.logger.info(
                f"[{idx}/{len(repositories)}] Processing repository: {repo_name}"
            )

            repo_result = {
                "repo_name": repo_name,
                "status": "failure",
                "pr_url": None,
                "pr_number": None,
                "branch_name": None,
                "major_version_updates": [],
                "remediation_duration_ms": 0,
                "pr_duration_ms": 0,
                "error": None,
                "total_cost_usd": None
            }

            try:
                # Step 1: Execute dependency remediation activity
                workflow.logger.info(
                    f"[{idx}/{len(repositories)}] Step 1: Running dependency remediation for {repo_name}"
                )

                remediation_payload = {
                    "org": org,
                    "repository": repository
                }

                remediation_result = await workflow.execute_activity(
                    "execute_dependency_remediation_activity",
                    remediation_payload,
                    start_to_close_timeout=timedelta(minutes=30),
                    retry_policy=DEPENDENCY_REMEDIATION_RETRY_POLICY,
                    heartbeat_timeout=timedelta(minutes=30),
                )

                repo_result["remediation_duration_ms"] = remediation_result.get("duration_ms", 0)
                repo_result["branch_name"] = remediation_result.get("branch_name")
                repo_result["major_version_updates"] = remediation_result.get("major_version_updates", [])

                # Check if remediation was successful and produced a branch
                if remediation_result.get("status") != "success":
                    repo_result["error"] = remediation_result.get("error", "Dependency remediation failed")
                    repo_result["total_cost_usd"] = remediation_result.get("total_cost_usd")
                    results["failed_repos"] += 1
                    results["results"].append(repo_result)
                    workflow.logger.warning(
                        f"[{idx}/{len(repositories)}] Dependency remediation failed for {repo_name}: "
                        f"{repo_result['error']}"
                    )
                    continue

                branch_name = remediation_result.get("branch_name")
                if not branch_name:
                    repo_result["error"] = "No branch created by remediation"
                    repo_result["total_cost_usd"] = remediation_result.get("total_cost_usd")
                    results["failed_repos"] += 1
                    results["results"].append(repo_result)
                    workflow.logger.warning(
                        f"[{idx}/{len(repositories)}] No branch created for {repo_name}"
                    )
                    continue

                workflow.logger.info(
                    f"[{idx}/{len(repositories)}] Dependency remediation successful for {repo_name}: "
                    f"branch={branch_name}"
                )

                # Step 2: Execute pull request activity
                workflow.logger.info(
                    f"[{idx}/{len(repositories)}] Step 2: Creating pull request for {repo_name}"
                )

                pr_payload = {
                    "org": org,
                    "repo_name": repo_name,
                    "branch_name": branch_name,
                    "vulnerability_data": remediation_result.get("vulnerability_data", {}),
                    "workspace_dir": remediation_result.get("workspace_dir"),
                    "major_version_updates": remediation_result.get("major_version_updates", []),
                    "auto_review": auto_review
                }

                pr_result = await workflow.execute_activity(
                    "execute_pull_request_activity",
                    pr_payload,
                    start_to_close_timeout=timedelta(minutes=30),
                    retry_policy=PULL_REQUEST_RETRY_POLICY,
                    heartbeat_timeout=timedelta(minutes=30),
                )

                repo_result["pr_duration_ms"] = pr_result.get("duration_ms", 0)
                repo_result["pr_url"] = pr_result.get("pr_url")
                repo_result["pr_number"] = pr_result.get("pr_number")

                # Calculate total cost
                remediation_cost = remediation_result.get("total_cost_usd") or 0
                pr_cost = pr_result.get("total_cost_usd") or 0
                repo_result["total_cost_usd"] = remediation_cost + pr_cost

                if pr_result.get("status") == "success" and pr_result.get("pr_url"):
                    repo_result["status"] = "success"
                    results["successful_repos"] += 1
                    workflow.logger.info(
                        f"[{idx}/{len(repositories)}] Successfully remediated {repo_name}: "
                        f"PR={pr_result.get('pr_url')}"
                    )
                else:
                    repo_result["error"] = pr_result.get("error", "PR creation failed")
                    results["failed_repos"] += 1
                    workflow.logger.warning(
                        f"[{idx}/{len(repositories)}] PR creation failed for {repo_name}: "
                        f"{repo_result['error']}"
                    )

                results["results"].append(repo_result)

            except Exception as e:
                # Handle activity execution failure
                results["failed_repos"] += 1
                error_msg = str(e)
                repo_result["error"] = f"Activity execution failed: {error_msg}"

                workflow.logger.error(
                    f"[{idx}/{len(repositories)}] Activity execution failed for {repo_name}: {error_msg}"
                )

                results["results"].append(repo_result)
        
        # Determine overall status
        if results["failed_repos"] == 0 and results["skipped_repos"] < results["total_repos"]:
            results["status"] = "success"
        elif results["successful_repos"] > 0:
            results["status"] = "partial"
        else:
            results["status"] = "failure"
        
        workflow.logger.info(
            f"RemediationOrchestratorWorkflow completed: "
            f"status={results['status']}, "
            f"successful={results['successful_repos']}, "
            f"failed={results['failed_repos']}, "
            f"skipped={results['skipped_repos']}"
        )
        
        return results