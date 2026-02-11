"""
Temporal activity for executing Claude agent remediation on a single repository.
"""
from typing import Any, Dict
from temporalio import activity
from pathlib import Path
import json
from datetime import datetime

from app.agents.remediation_agent import run_remediation_agent


@activity.defn(name="execute_agent_activity")
async def execute_agent_activity(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute Claude agent to remediate a single repository's vulnerabilities.
    
    This activity wraps the remediation agent and handles:
    - Creating vulnerability-object.json for the target repository
    - Setting up workspace directory
    - Invoking the agent
    - Returning structured results
    
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
            "status": "success" | "failure",
            "repo_name": "python-uv-test",
            "pr_urls": ["https://github.com/.../pull/123"],
            "duration_ms": 45000,
            "error": null | "error message",
            "total_cost_usd": 0.05,
            "num_turns": 12
        }
    """
    activity.logger.info("Starting execute agent activity")
    
    org = payload.get("org")
    repository = payload.get("repository")
    
    if not org:
        raise ValueError("Missing required parameter: org")
    if not repository:
        raise ValueError("Missing required parameter: repository")
    
    repo_name = repository.get("name", "unknown")
    
    activity.logger.info(
        f"Executing agent for repository: {org}/{repo_name}"
    )
    
    # Create workspace directory for this execution
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    workspace_dir = Path("workspace") / f"{repo_name}_{timestamp}"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    # Create log directory
    log_dir = Path("logs") / f"agent_{repo_name}_{timestamp}"
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
    activity.heartbeat(f"Starting agent for {repo_name}")
    
    try:
        # Execute the remediation agent
        result = await run_remediation_agent(
            org=org,
            repository_data=repository,
            workspace_dir=workspace_dir,
            log_dir=log_dir
        )
        
        activity.logger.info(
            f"Agent execution completed for {repo_name}: "
            f"status={result['status']}, "
            f"pr_urls={result['pr_urls']}, "
            f"duration={result['duration_ms']}ms"
        )
        
        # Send final heartbeat
        activity.heartbeat(f"Completed: {result['status']}")
        
        return result
    
    except Exception as e:
        activity.logger.error(
            f"Agent execution failed for {repo_name}: {str(e)}",
            exc_info=True
        )
        
        return {
            "status": "failure",
            "repo_name": repo_name,
            "pr_urls": [],
            "duration_ms": 0,
            "error": str(e),
            "total_cost_usd": None,
            "num_turns": 0
        }