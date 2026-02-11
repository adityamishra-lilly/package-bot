import os
from typing import Any, Dict, List, Optional
import requests
from temporalio import activity

GITHUB_API = "https://api.github.com"

def _auth_headers(token: str) -> Dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "temporal-dependabot-planner/1.0",
    }

@activity.defn(name="fetch_dependabot_alerts_activity")
async def fetch_dependabot_alerts_activity(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Fetch Dependabot alerts for an organization.

    Args:
        payload: Dictionary containing:
                {
                    "org": "organization-name",
                    "state": "open",  # optional, defaults to "open"
                    "severities": ["high", "critical"],  # optional
                    "per_page": 100  # optional, defaults to 100
                }

    Returns:
        Dictionary containing results:
        {
            "alerts": [...],  # list of alert dictionaries
            "count": 42
        }
    """
    activity.logger.info("Starting fetch Dependabot alerts activity")

    org = payload.get("org")
    state = payload.get("state", "open")
    severities = payload.get("severities")
    per_page = payload.get("per_page", 100)

    if not org:
        raise ValueError("Missing required parameter: org")

    activity.logger.info(
        f"Fetching Dependabot alerts for org: {org}, state: {state}, severities: {severities}"
    )

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN not found in environment variables")
    
    url = f"{GITHUB_API}/orgs/{org}/dependabot/alerts"
    params = {"state": state, "per_page": per_page}
    if severities:
        params["severity"] = ",".join(severities)

    alerts: List[Dict[str, Any]] = []
    next_url = url
    next_params = params
    page_count = 0
    
    while next_url:
        page_count += 1
        activity.logger.info(f"Fetching page {page_count} from GitHub API")
        
        r = requests.get(next_url, headers=_auth_headers(token), params=next_params, timeout=30)
        r.raise_for_status()
        batch = r.json()
        if isinstance(batch, dict):
            batch = batch.get("items", [])
        alerts.extend(batch)

        activity.logger.info(f"Retrieved {len(batch)} alerts from page {page_count}")

        # Follow Link: <url>; rel="next"
        link = r.headers.get("Link", "")
        next_url, next_params = None, None
        if link:
            for part in [p.strip() for p in link.split(",")]:
                if 'rel="next"' in part:
                    lt, gt = part.find("<"), part.find(">")
                    if lt >= 0 and gt > lt:
                        next_url = part[lt+1:gt]
                    break

    activity.logger.info(
        f"Completed: fetched {len(alerts)} total alerts across {page_count} pages"
    )

    return {
        "alerts": alerts,
        "count": len(alerts)
    }
