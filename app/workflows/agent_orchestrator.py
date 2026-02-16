"""
Remediation orchestrator workflow for a single repository.

Each instance of this workflow processes one repository through three activities:
1. execute_dependency_remediation_activity - Updates dependencies, creates branch
2. execute_pull_request_activity - Creates and reviews PR from the fix branch
3. execute_jira_ticket_activity - Creates Jira ticket to track PR review (non-critical)

The parent PackagebotWorkflow spawns one instance per repository.
"""
from datetime import timedelta
from typing import Any, Dict
from temporalio import workflow
from temporalio.common import RetryPolicy

# Retry policy for dependency remediation activity (3 attempts)
DEPENDENCY_REMEDIATION_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    maximum_interval=timedelta(minutes=1),
    maximum_attempts=3,
)

# Retry policy for pull request activity (2 attempts)
PULL_REQUEST_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=2,
)

# Retry policy for Jira ticket activity (2 attempts, non-critical)
JIRA_TICKET_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=2,
)


@workflow.defn
class RemediationOrchestratorWorkflow:
    """
    Orchestrator workflow for executing agent remediation on a single repository.

    This workflow:
    1. Receives a single repository with its security alerts
    2. Executes dependency remediation, PR creation, and Jira ticket creation
    3. Returns the result for this repository
    """

    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute remediation for a single repository.

        Executes three activities in sequence:
        1. execute_dependency_remediation_activity - Updates dependencies
        2. execute_pull_request_activity - Creates PR from fix branch
        3. execute_jira_ticket_activity - Creates Jira ticket (non-critical)

        Args:
            input_data: Dictionary containing:
                {
                    "org": "AgentPOC-Org",
                    "repository": {
                        "name": "python-uv-test",
                        "html_url": "...",
                        "security_alerts": [...]
                    },
                    "auto_review": true  # optional, default true
                }

        Returns:
            Dictionary containing:
            {
                "repo_name": "python-uv-test",
                "status": "success" | "failure",
                "pr_url": "https://github.com/.../pull/123",
                "pr_number": 123,
                "branch_name": "fix/security-alerts-...",
                "major_version_updates": [...],
                "remediation_duration_ms": 45000,
                "pr_duration_ms": 15000,
                "jira_key": "PROJ-456",
                "jira_url": "https://...",
                "jira_duration_ms": 10000,
                "error": null,
                "total_cost_usd": 0.05
            }
        """
        org = input_data.get("org")
        repository = input_data.get("repository", {})
        auto_review = input_data.get("auto_review", True)
        repo_name = repository.get("name", "unknown")

        if not org:
            raise ValueError("Missing required parameter: org")
        if not repository:
            raise ValueError("Missing required parameter: repository")

        workflow.logger.info(
            f"Starting RemediationOrchestratorWorkflow for {org}/{repo_name}"
        )

        result = {
            "repo_name": repo_name,
            "status": "failure",
            "pr_url": None,
            "pr_number": None,
            "branch_name": None,
            "major_version_updates": [],
            "remediation_duration_ms": 0,
            "pr_duration_ms": 0,
            "jira_key": None,
            "jira_url": None,
            "jira_duration_ms": 0,
            "error": None,
            "total_cost_usd": None,
        }

        try:
            # Step 1: Execute dependency remediation activity
            workflow.logger.info(
                f"Step 1: Running dependency remediation for {repo_name}"
            )

            remediation_payload = {
                "org": org,
                "repository": repository,
            }

            remediation_result = await workflow.execute_activity(
                "execute_dependency_remediation_activity",
                remediation_payload,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=DEPENDENCY_REMEDIATION_RETRY_POLICY,
                heartbeat_timeout=timedelta(minutes=30),
            )

            result["remediation_duration_ms"] = remediation_result.get("duration_ms", 0)
            result["branch_name"] = remediation_result.get("branch_name")
            result["major_version_updates"] = remediation_result.get("major_version_updates", [])

            # Check if remediation was successful and produced a branch
            if remediation_result.get("status") != "success":
                result["error"] = remediation_result.get("error", "Dependency remediation failed")
                result["total_cost_usd"] = remediation_result.get("total_cost_usd")
                workflow.logger.warning(
                    f"Dependency remediation failed for {repo_name}: {result['error']}"
                )
                return result

            branch_name = remediation_result.get("branch_name")
            if not branch_name:
                result["error"] = "No branch created by remediation"
                result["total_cost_usd"] = remediation_result.get("total_cost_usd")
                workflow.logger.warning(f"No branch created for {repo_name}")
                return result

            workflow.logger.info(
                f"Dependency remediation successful for {repo_name}: branch={branch_name}"
            )

            # Step 2: Execute pull request activity
            workflow.logger.info(f"Step 2: Creating pull request for {repo_name}")

            pr_payload = {
                "org": org,
                "repo_name": repo_name,
                "branch_name": branch_name,
                "vulnerability_data": remediation_result.get("vulnerability_data", {}),
                "workspace_dir": remediation_result.get("workspace_dir"),
                "major_version_updates": remediation_result.get("major_version_updates", []),
                "auto_review": auto_review,
            }

            pr_result = await workflow.execute_activity(
                "execute_pull_request_activity",
                pr_payload,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=PULL_REQUEST_RETRY_POLICY,
                heartbeat_timeout=timedelta(minutes=30),
            )

            result["pr_duration_ms"] = pr_result.get("duration_ms", 0)
            result["pr_url"] = pr_result.get("pr_url")
            result["pr_number"] = pr_result.get("pr_number")

            # Calculate total cost
            remediation_cost = remediation_result.get("total_cost_usd") or 0
            pr_cost = pr_result.get("total_cost_usd") or 0
            result["total_cost_usd"] = remediation_cost + pr_cost

            if pr_result.get("status") == "success" and pr_result.get("pr_url"):
                result["status"] = "success"
                workflow.logger.info(
                    f"Successfully remediated {repo_name}: PR={pr_result.get('pr_url')}"
                )

                # Step 3: Execute Jira ticket activity (non-critical)
                try:
                    workflow.logger.info(
                        f"Step 3: Creating Jira ticket for {repo_name}"
                    )

                    jira_payload = {
                        "org": org,
                        "repo_name": repo_name,
                        "pr_url": pr_result.get("pr_url"),
                        "pr_number": pr_result.get("pr_number"),
                        "branch_name": branch_name,
                        "vulnerability_data": remediation_result.get("vulnerability_data", {}),
                        "workspace_dir": remediation_result.get("workspace_dir"),
                        "major_version_updates": remediation_result.get("major_version_updates", []),
                    }

                    jira_result = await workflow.execute_activity(
                        "execute_jira_ticket_activity",
                        jira_payload,
                        start_to_close_timeout=timedelta(minutes=30),
                        retry_policy=JIRA_TICKET_RETRY_POLICY,
                        heartbeat_timeout=timedelta(minutes=30),
                    )

                    result["jira_duration_ms"] = jira_result.get("duration_ms", 0)
                    result["jira_key"] = jira_result.get("jira_key")
                    result["jira_url"] = jira_result.get("jira_url")

                    # Add Jira cost to total
                    jira_cost = jira_result.get("total_cost_usd") or 0
                    result["total_cost_usd"] = (result["total_cost_usd"] or 0) + jira_cost

                    if jira_result.get("status") == "success":
                        workflow.logger.info(
                            f"Jira ticket created for {repo_name}: "
                            f"{jira_result.get('jira_key')}"
                        )
                    else:
                        workflow.logger.warning(
                            f"Jira ticket creation failed for {repo_name}: "
                            f"{jira_result.get('error', 'Unknown error')} (non-critical)"
                        )
                except Exception as jira_err:
                    # Jira failure is non-critical - don't change repo status
                    workflow.logger.warning(
                        f"Jira ticket activity failed for {repo_name}: "
                        f"{str(jira_err)} (non-critical, PR was created successfully)"
                    )
            else:
                result["error"] = pr_result.get("error", "PR creation failed")
                workflow.logger.warning(
                    f"PR creation failed for {repo_name}: {result['error']}"
                )

        except Exception as e:
            error_msg = str(e)
            result["error"] = f"Activity execution failed: {error_msg}"
            workflow.logger.error(
                f"Activity execution failed for {repo_name}: {error_msg}"
            )

        workflow.logger.info(
            f"RemediationOrchestratorWorkflow completed for {repo_name}: "
            f"status={result['status']}"
        )

        return result
