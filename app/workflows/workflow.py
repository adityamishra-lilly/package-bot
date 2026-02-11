from datetime import timedelta
from typing import Any, Dict
from temporalio import workflow, exceptions
from temporalio.common import RetryPolicy

from app.workflows.agent_orchestrator import RemediationOrchestratorWorkflow

# Task queue constant
PACKAGEBOT_TASK_QUEUE = "packagebot-task-queue"

# Retry policy constants for activities
FETCH_ALERTS_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=5,
)

BUILD_ALERTS_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=10),
    maximum_attempts=3,
)

LOAD_PLAN_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=5),
    maximum_attempts=3,
)

# Type aliases for improved readability
WorkflowPayload = Dict[str, Any]
WorkflowResult = Dict[str, Any]


# ============================================================================
# Child Workflow
# ============================================================================

@workflow.defn
class DependabotAlertsWorkflow:
    """Child workflow for fetching Dependabot alerts and building remediation plan."""

    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Dependabot alert processing activities in sequence:
        1. Fetch Dependabot alerts from GitHub API
        2. Build remediation plan object from raw alerts
        3. Load remediation plan to get repositories data

        Args:
            input_data: Input data containing:
                - org: Organization name (required)
                - state: Alert state (optional, defaults to "open")
                - severities: List of severities to filter (optional)
                - per_page: Results per page (optional, defaults to 100)
                - workflow_id: Workflow identifier (optional)

        Returns:
            Dictionary containing workflow results with alert and remediation data
        """

        workflow.logger.info(
            f"Starting Dependabot Alerts workflow with input: {input_data}"
        )

        workflow_id = input_data.get("workflow_id", "dependabot-alerts")
        org = input_data.get("org")
        state = input_data.get("state", "open")
        severities = input_data.get("severities")
        per_page = input_data.get("per_page", 100)

        if not org:
            raise ValueError("Missing required parameter: org")

        results = {
            "workflow_id": workflow_id,
            "workflow_type": "dependabot_alerts",
            "status": "success",
            "org": org,
            "fetch_result": None,
            "build_result": None,
            "load_result": None,
            "repositories": [],
        }

        # Step 1: Fetch Dependabot alerts
        workflow.logger.info(
            f"Step 1: Fetching Dependabot alerts for org: {org}, state: {state}"
        )
        fetch_payload = {
            "org": org,
            "state": state,
            "per_page": per_page,
        }
        if severities:
            fetch_payload["severities"] = severities

        fetch_result = await workflow.execute_activity(
            "fetch_dependabot_alerts_activity",
            fetch_payload,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=FETCH_ALERTS_RETRY_POLICY,
        )

        # Validate fetch activity result
        if not isinstance(fetch_result, dict) or "alerts" not in fetch_result:
            raise exceptions.ApplicationError(
                f"fetch_dependabot_alerts_activity returned invalid result: {fetch_result}"
            )

        results["fetch_result"] = {
            "count": fetch_result.get("count", 0),
            "status": "success",
        }
        workflow.logger.info(
            f"Fetched {fetch_result.get('count', 0)} Dependabot alerts"
        )

        # Step 2: Build alerts object (remediation plan)
        workflow.logger.info("Step 2: Building remediation plan from alerts")
        build_payload = {
            "org": org,
            "raw_alerts": fetch_result.get("alerts", []),
        }

        build_result = await workflow.execute_activity(
            "build_alerts_object_activity",
            build_payload,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=BUILD_ALERTS_RETRY_POLICY,
        )

        # Validate build activity result
        if build_result.get("status") not in {"success", "SUCCESS", "COMPLETED"}:
            raise exceptions.ApplicationError(
                f"build_alerts_object_activity returned error status: {build_result.get('status')}"
            )

        results["build_result"] = {
            "file_path": build_result.get("file_path"),
            "repo_count": build_result.get("repo_count", 0),
            "alert_count": build_result.get("alert_count", 0),
            "status": build_result.get("status"),
        }
        workflow.logger.info(
            f"Remediation plan built: {build_result.get('alert_count', 0)} alerts "
            f"across {build_result.get('repo_count', 0)} repositories"
        )

        # Step 3: Load remediation plan to get repositories data
        workflow.logger.info("Step 3: Loading remediation plan to get repositories")
        load_payload = {
            "remediation_plan_path": build_result.get("file_path"),
        }

        load_result = await workflow.execute_activity(
            "load_remediation_plan_activity",
            load_payload,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=LOAD_PLAN_RETRY_POLICY,
        )

        # Validate load activity result
        if load_result.get("status") != "success":
            raise exceptions.ApplicationError(
                f"load_remediation_plan_activity failed: {load_result.get('error')}"
            )

        repositories = load_result.get("repositories", [])
        results["load_result"] = {
            "repo_count": len(repositories),
            "status": load_result.get("status"),
        }
        results["repositories"] = repositories
        
        workflow.logger.info(
            f"Loaded {len(repositories)} repositories from remediation plan"
        )

        workflow.logger.info(
            f"Dependabot Alerts workflow completed successfully for org: {org}"
        )
        return results


# ============================================================================
# Parent Workflow
# ============================================================================

@workflow.defn
class PackagebotWorkflow:
    """Parent workflow that orchestrates Dependabot alert processing and remediation."""

    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the Packagebot workflow:
        1. Execute DependabotAlertsWorkflow child workflow
        2. Execute RemediationOrchestratorWorkflow child workflow
        3. Return aggregated results

        Args:
            input_data: Input data containing workflow configuration and parameters
                {
                    "workflow_id": "packagebot-workflow",
                    "org": "AgentPOC-Org",
                    "state": "open",
                    "enable_remediation": true  # Enable agent remediation (default: false)
                }

        Returns:
            Dictionary containing workflow results
        """

        workflow.logger.info(
            f"Starting Packagebot parent workflow with input: {input_data}"
        )

        workflow_id = input_data.get("workflow_id", "packagebot-workflow")
        enable_remediation = input_data.get("enable_remediation", False)

        parent_results = {
            "workflow_id": workflow_id,
            "status": "success",
            "alerts_workflow_result": None,
            "remediation_workflow_result": None,
            "execution_summary": {},
        }

        # Step 1: Execute DependabotAlertsWorkflow as child workflow
        workflow.logger.info(
            "Step 1: Executing DependabotAlertsWorkflow child workflow..."
        )

        try:
            child_input = {
                "workflow_id": f"{workflow_id}-dependabot-alerts",
                **input_data,
            }

            alerts_result = await workflow.execute_child_workflow(
                DependabotAlertsWorkflow.run,
                child_input,
                id=f"dependabot-alerts-{workflow.info().workflow_id}",
                task_queue=PACKAGEBOT_TASK_QUEUE,
            )

            parent_results["alerts_workflow_result"] = alerts_result
            workflow.logger.info(
                f"DependabotAlertsWorkflow completed successfully"
            )

            # Build intermediate summary
            build_result = alerts_result.get("build_result", {})
            load_result = alerts_result.get("load_result", {})
            org = alerts_result.get("org")
            repositories = alerts_result.get("repositories", [])
            
            parent_results["execution_summary"] = {
                "org": org,
                "alerts_fetched": alerts_result.get("fetch_result", {}).get("count", 0),
                "repos_analyzed": build_result.get("repo_count", 0),
                "unique_alerts": build_result.get("alert_count", 0),
                "remediation_plan_path": build_result.get("file_path"),
                "repositories_loaded": load_result.get("repo_count", 0),
                "remediation_enabled": enable_remediation,
                "status": "alerts_completed",
            }

        except Exception as e:
            workflow.logger.error(
                f"PackagebotWorkflow failed during alerts workflow execution: {str(e)}"
            )
            raise

        # Step 2: Execute RemediationOrchestratorWorkflow if enabled
        if enable_remediation:
            workflow.logger.info(
                "Step 2: Executing RemediationOrchestratorWorkflow child workflow..."
            )
            
            try:
                # Use repositories data from DependabotAlertsWorkflow result
                if not repositories:
                    workflow.logger.warning("No repositories found in remediation plan, skipping remediation")
                    parent_results["execution_summary"]["status"] = "completed_no_repos"
                else:
                    # Execute remediation orchestrator
                    remediation_input = {
                        "workflow_id": f"{workflow_id}-remediation",
                        "org": org,
                        "remediation_plan_path": build_result.get("file_path"),
                        "repositories": repositories,
                        "skip_repos": input_data.get("skip_repos", [])
                    }
                    
                    remediation_result = await workflow.execute_child_workflow(
                        RemediationOrchestratorWorkflow.run,
                        remediation_input,
                        id=f"remediation-{workflow.info().workflow_id}",
                        task_queue=PACKAGEBOT_TASK_QUEUE,
                    )
                
                    parent_results["remediation_workflow_result"] = remediation_result
                    workflow.logger.info(
                        f"RemediationOrchestratorWorkflow completed: "
                        f"status={remediation_result.get('status')}"
                    )
                    
                    # Update execution summary with remediation results
                    parent_results["execution_summary"].update({
                        "remediation_status": remediation_result.get("status"),
                        "total_repos_processed": remediation_result.get("total_repos", 0),
                        "successful_remediations": remediation_result.get("successful_repos", 0),
                        "failed_remediations": remediation_result.get("failed_repos", 0),
                        "skipped_repos": remediation_result.get("skipped_repos", 0),
                        "status": "completed_with_remediation"
                    })
                
            except Exception as e:
                workflow.logger.error(
                    f"PackagebotWorkflow failed during remediation workflow execution: {str(e)}"
                )
                parent_results["execution_summary"]["remediation_error"] = str(e)
                parent_results["execution_summary"]["status"] = "remediation_failed"
                # Don't raise - allow workflow to complete with partial results
        else:
            workflow.logger.info(
                "Step 2: Remediation disabled, skipping RemediationOrchestratorWorkflow"
            )
            parent_results["execution_summary"]["status"] = "completed"

        workflow.logger.info(
            f"Packagebot workflow completed: {parent_results['execution_summary']}"
        )
        return parent_results
