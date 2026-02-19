"""
Jira Ticket Agent - Main orchestration module.

This agent handles Jira ticket creation and review as a separate concern
from pull request creation. It orchestrates two subagents:
1. Creator - Creates Bug issues in Jira to track security PR review
2. Reviewer - Validates ticket quality and can self-correct
"""

from claude_agent_sdk import (
    ClaudeSDKClient,
    ThinkingBlock,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    HookMatcher,
)
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from app.mcp.github_mcp import get_github_mcp_config, get_github_mcp_tools
from app.mcp.jira_mcp import get_jira_mcp_config, get_jira_mcp_tools
from app.utils.agentlogging import TranscriptWriter, ObservabilityLogger

from .subagents import (
    creator_agent,
    reviewer_agent,
)

# Tools available to the main orchestrator
JIRA_ORCHESTRATOR_APPROVED_TOOLS = [
    "Read",
    "Grep",
    "Bash",
    "Glob",
    "TodoWrite",
    "Skill",
    "Task",
] + get_jira_mcp_tools() + get_github_mcp_tools()


async def run_jira_ticket_agent(
    org: str,
    repo_name: str,
    pr_url: str,
    pr_number: int,
    branch_name: str,
    vulnerability_data: Dict[str, Any],
    workspace_dir: Path,
    log_dir: Path | None = None,
    major_version_updates: List[str] | None = None,
    project_key: str | None = None,
) -> Dict[str, Any]:
    """
    Run the Jira ticket agent to create and review a tracking ticket.

    This agent is called AFTER the pull request agent has:
    1. Created a PR from the fix branch
    2. Reviewed the PR quality

    Args:
        org: GitHub organization name
        repo_name: Repository name
        pr_url: URL of the created pull request
        pr_number: PR number
        branch_name: Fix branch name
        vulnerability_data: Original vulnerability object with CVE details
        workspace_dir: Working directory
        log_dir: Optional directory for storing logs
        major_version_updates: List of packages with major version updates
        project_key: Jira project key (if None, agent will determine from context)

    Returns:
        {
            "status": "success" | "failure",
            "jira_key": str | None,
            "jira_url": str | None,
            "review_status": str | None,
            "duration_ms": int,
            "error": None | str,
            "total_cost_usd": float | None
        }
    """
    start_time = datetime.now()

    # Create log directory if not provided
    if log_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path("logs") / f"jira_{repo_name}_{timestamp}"

    log_dir.mkdir(parents=True, exist_ok=True)
    transcript_file = log_dir / "transcript.txt"

    # Compute severity-based priority from vulnerability data
    severity_priority_map = {
        "critical": "Highest",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
    }
    highest_severity = "low"
    severity_order = ["low", "medium", "high", "critical"]
    alerts = vulnerability_data.get("repository", {}).get("security_alerts", [])
    if not alerts and isinstance(vulnerability_data, dict):
        alerts = vulnerability_data.get("security_alerts", [])

    for alert in alerts:
        sev = alert.get("severity", "low").lower()
        if sev in severity_order and severity_order.index(sev) > severity_order.index(highest_severity):
            highest_severity = sev

    jira_priority = severity_priority_map.get(highest_severity, "Medium")

    # Build severity counts
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for alert in alerts:
        sev = alert.get("severity", "low").lower()
        if sev in severity_counts:
            severity_counts[sev] += 1

    major_updates_str = ""
    if major_version_updates:
        major_updates_str = f"""
    MAJOR VERSION UPDATES:
    The following packages have major version bumps - flag these prominently:
    {', '.join(major_version_updates)}
    """

    project_key_str = ""
    if project_key:
        project_key_str = f"- Jira Project Key: {project_key}"

    # System prompt for the orchestrator
    instructions = f"""
    You are a Jira ticket orchestrator. Your job is to create and review Jira Bug issues
    to track review of security pull requests.

    Use the 'memory' mcp server to track a list of TODOs for the Jira ticket workflow
    and update them as you complete each step.

    CONTEXT:
    - Organization: {org}
    - Repository: {repo_name}
    - PR URL: {pr_url}
    - PR Number: #{pr_number}
    - Branch: {branch_name}
    - Highest Severity: {highest_severity}
    - Recommended Jira Priority: {jira_priority}
    - Severity Counts: Critical={severity_counts['critical']}, High={severity_counts['high']}, Medium={severity_counts['medium']}, Low={severity_counts['low']}
    {project_key_str}
    {major_updates_str}

    WORKFLOW:

    1. TICKET CREATION (creator-agent):
       - Call the creator-agent to create the Jira Bug issue
       - Provide all vulnerability details for the description
       - Use priority: {jira_priority} (mapped from highest severity: {highest_severity})
       - Labels: ["security", "dependabot", "automated"]
       - Get the Jira key and URL

    2. TICKET REVIEW (reviewer-agent):
       - Call the reviewer-agent to validate the ticket
       - Check description completeness
       - Verify priority and labels
       - Fix any issues found

    IMPORTANT:
    - Issue type MUST be Bug
    - Description uses PLAIN TEXT (Jira MCP converts to ADF internally)
    - Include the PR URL: {pr_url}
    - Include ALL CVE/GHSA identifiers from vulnerability data
    - Priority should be: {jira_priority}

    OUTPUT:
    After workflow completes, summarize:
    - Jira Key (e.g., PROJ-456)
    - Jira URL
    - Review status
    """

    async def start_jira_workflow():
        yield {
            "type": "user",
            "message": {
                "role": "user",
                "content": f"""Create a Jira Bug issue to track review of the security PR:

PR URL: {pr_url}
PR Number: #{pr_number}
Repository: {org}/{repo_name}
Branch: {branch_name}

Vulnerability data:
{_format_vulnerability_summary(alerts)}

Priority: {jira_priority} (based on highest severity: {highest_severity})
Labels: ["security", "dependabot", "automated"]

After creation, have the reviewer-agent verify the ticket quality.
"""
            }
        }

    result = {
        "status": "failure",
        "jira_key": None,
        "jira_url": None,
        "review_status": None,
        "duration_ms": 0,
        "error": None,
        "total_cost_usd": None
    }

    try:
        with TranscriptWriter(transcript_file) as transcript, \
             ObservabilityLogger(log_dir, transcript, agent_context="jira_ticket", workspace_dir=workspace_dir) as tool_logger:

            options = ClaudeAgentOptions(
                max_turns=500,
                permission_mode="acceptEdits",
                system_prompt=instructions,
                setting_sources=["project"],
                allowed_tools=JIRA_ORCHESTRATOR_APPROVED_TOOLS,
                agents={
                    "creator-agent": creator_agent,
                    "reviewer-agent": reviewer_agent,
                },
                mcp_servers={
                    "memory": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-memory"]
                    },
                    "github": get_github_mcp_config(),
                    "jira": get_jira_mcp_config(),
                },
                hooks={
                    "PreToolUse": [
                        HookMatcher(hooks=[tool_logger.get_pre_tool_hook()])
                    ],
                    "PostToolUse": [
                        HookMatcher(hooks=[tool_logger.get_post_tool_hook()])
                    ],
                },
                cwd=str(workspace_dir),
            )

            transcript.write(f"=== Jira Ticket Creation Started: {start_time.strftime('%Y%m%d_%H%M%S')} ===\n")
            transcript.write(f"Repository: {org}/{repo_name}\n")
            transcript.write(f"PR: {pr_url}\n")
            transcript.write(f"Priority: {jira_priority}\n")
            transcript.write(f"Log directory: {log_dir}\n")
            transcript.write("=" * 60 + "\n\n")

            async with ClaudeSDKClient(options) as client:
                await client.query(start_jira_workflow())

                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                transcript.write(f"[ASSISTANT] {block.text}\n")
                                logging.debug(block.text)

                                # Extract Jira key (e.g., PROJ-123)
                                key_match = re.search(
                                    r'\b([A-Z][A-Z0-9]+-\d+)\b',
                                    block.text
                                )
                                if key_match:
                                    result["jira_key"] = key_match.group(1)

                                # Extract Jira URL
                                url_match = re.search(
                                    r'https://[^/]+\.atlassian\.net/browse/[A-Z][A-Z0-9]+-\d+',
                                    block.text
                                )
                                if url_match:
                                    result["jira_url"] = url_match.group(0)

                                # Extract review status
                                if "APPROVED" in block.text.upper() and "CHANGES_REQUESTED" not in block.text.upper():
                                    result["review_status"] = "approved"
                                elif "FIXED" in block.text.upper():
                                    result["review_status"] = "fixed"
                                elif "CHANGES_REQUESTED" in block.text.upper():
                                    result["review_status"] = "changes_requested"

                            if isinstance(block, ThinkingBlock):
                                transcript.write(f"[THINKING] {block.thinking}\n")
                                logging.debug(block.thinking)

                    # Check for ResultMessage
                    if hasattr(message, 'subtype'):
                        if message.subtype == "success":
                            result["status"] = "success"
                            result["total_cost_usd"] = getattr(message, 'total_cost_usd', None)
                        elif message.subtype == "error":
                            result["status"] = "failure"
                            result["error"] = getattr(message, 'result', "Unknown error")

            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            result["duration_ms"] = duration_ms

            transcript.write("\n" + "=" * 60 + "\n")
            transcript.write(f"=== Jira Ticket Creation Completed: {end_time.strftime('%Y%m%d_%H%M%S')} ===\n")
            transcript.write(f"Status: {result['status']}\n")
            transcript.write(f"Jira Key: {result['jira_key']}\n")
            transcript.write(f"Jira URL: {result['jira_url']}\n")
            transcript.write(f"Review: {result['review_status']}\n")
            transcript.write(f"Duration: {duration_ms}ms\n")

            logging.info(f"Jira ticket creation complete for {repo_name}: {result['status']}")

    except Exception as e:
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        result["duration_ms"] = duration_ms
        result["error"] = str(e)
        result["status"] = "failure"
        logging.error(f"Jira ticket creation failed for {repo_name}: {e}", exc_info=True)

    return result


def _format_vulnerability_summary(alerts: List[Dict[str, Any]]) -> str:
    """Format vulnerability alerts into a readable summary for the agent."""
    if not alerts:
        return "No vulnerability data available."

    lines = []
    for alert in alerts:
        package = alert.get("package", "unknown")
        current = alert.get("current_version", "unknown")
        target = alert.get("target_version", "unknown")
        severity = alert.get("severity", "unknown")
        cvss = alert.get("highest_cvss", "N/A")
        cves = ", ".join(alert.get("cves", []))
        ghsas = ", ".join(alert.get("ghsas", []))

        lines.append(
            f"- {package}: {current} → {target} | {severity} (CVSS: {cvss}) | "
            f"CVEs: {cves or 'N/A'} | GHSAs: {ghsas or 'N/A'}"
        )

    return "\n".join(lines)
