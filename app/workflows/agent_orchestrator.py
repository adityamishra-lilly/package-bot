"""
Remediation orchestrator workflow for processing multiple repositories.
"""
from datetime import timedelta
from typing import Any, Dict, List
from temporalio import workflow
from temporalio.common import RetryPolicy

# Retry policy for agent execution activity (3 attempts, 10 min timeout)
AGENT_EXECUTION_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    maximum_interval=timedelta(minutes=1),
    maximum_attempts=3,
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
                    "skip_repos": []  # optional
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
                        "pr_urls": [...],
                        "duration_ms": 45000,
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
                    "pr_urls": [],
                    "duration_ms": 0,
                    "error": "Repository in skip list"
                })
                continue
            
            workflow.logger.info(
                f"[{idx}/{len(repositories)}] Processing repository: {repo_name}"
            )
            
            # Execute agent remediation activity
            agent_payload = {
                "org": org,
                "repository": repository
            }
            
            try:
                agent_result = await workflow.execute_activity(
                    "execute_agent_activity",
                    agent_payload,
                    start_to_close_timeout=timedelta(minutes=15),
                    retry_policy=AGENT_EXECUTION_RETRY_POLICY,
                    heartbeat_timeout=timedelta(minutes=15),
                )
                
                # Track success/failure
                if agent_result.get("status") == "success":
                    results["successful_repos"] += 1
                    workflow.logger.info(
                        f"[{idx}/{len(repositories)}] Successfully remediated {repo_name}: "
                        f"PRs created: {len(agent_result.get('pr_urls', []))}"
                    )
                else:
                    results["failed_repos"] += 1
                    workflow.logger.warning(
                        f"[{idx}/{len(repositories)}] Failed to remediate {repo_name}: "
                        f"{agent_result.get('error', 'Unknown error')}"
                    )
                
                results["results"].append(agent_result)
            
            except Exception as e:
                # Handle activity execution failure
                results["failed_repos"] += 1
                error_msg = str(e)
                
                workflow.logger.error(
                    f"[{idx}/{len(repositories)}] Activity execution failed for {repo_name}: {error_msg}"
                )
                
                results["results"].append({
                    "repo_name": repo_name,
                    "status": "failure",
                    "pr_urls": [],
                    "duration_ms": 0,
                    "error": f"Activity execution failed: {error_msg}",
                    "total_cost_usd": None,
                    "num_turns": 0
                })
        
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