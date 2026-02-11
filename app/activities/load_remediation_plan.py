"""
Temporal activity for loading remediation plan from JSON file.
"""
from typing import Any, Dict
from temporalio import activity
from pathlib import Path
import json


@activity.defn(name="load_remediation_plan_activity")
async def load_remediation_plan_activity(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Load remediation plan from JSON file and return repositories data.
    
    This activity reads the remediation plan file created by build_alerts_object_activity
    and returns the repositories list to be used by the remediation workflow.
    
    Args:
        payload: Dictionary containing:
                {
                    "remediation_plan_path": "path/to/remediation-plan.json"
                }
    
    Returns:
        Dictionary containing:
        {
            "status": "success" | "failure",
            "repositories": [...],
            "error": null | "error message"
        }
    """
    activity.logger.info("Starting load remediation plan activity")
    
    remediation_plan_path = payload.get("remediation_plan_path")
    
    if not remediation_plan_path:
        raise ValueError("Missing required parameter: remediation_plan_path")
    
    try:
        # Read the remediation plan file
        plan_file = Path(remediation_plan_path)
        
        if not plan_file.exists():
            error_msg = f"Remediation plan not found at {remediation_plan_path}"
            activity.logger.error(error_msg)
            return {
                "status": "failure",
                "repositories": [],
                "error": error_msg
            }
        
        activity.logger.info(f"Reading remediation plan from {remediation_plan_path}")
        
        with open(plan_file, "r", encoding="utf-8") as f:
            remediation_plan = json.load(f)
        
        repositories = remediation_plan.get("repositories", [])
        
        activity.logger.info(
            f"Successfully loaded remediation plan with {len(repositories)} repositories"
        )
        
        return {
            "status": "success",
            "repositories": repositories,
            "error": None
        }
    
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in remediation plan file: {str(e)}"
        activity.logger.error(error_msg)
        return {
            "status": "failure",
            "repositories": [],
            "error": error_msg
        }
    
    except Exception as e:
        error_msg = f"Failed to load remediation plan: {str(e)}"
        activity.logger.error(error_msg, exc_info=True)
        return {
            "status": "failure",
            "repositories": [],
            "error": error_msg
        }