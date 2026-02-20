"""
Pull Request Agent - Main orchestration module.

This agent handles pull request creation and review as a separate concern
from dependency remediation. It orchestrates two subagents:
1. Creator - Creates well-formatted PRs
2. Reviewer - Reviews PRs for quality
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
from app.utils.agentlogging import TranscriptWriter, ObservabilityLogger

from .subagents import (
    creator_agent,
    reviewer_agent,
)

# Tools available to the main orchestrator
PR_ORCHESTRATOR_APPROVED_TOOLS = [
    "Read",
    "Grep",
    "Bash",
    "Glob",
    "TodoWrite",
    "Skill",
    "Task",
] + get_github_mcp_tools()


async def run_pull_request_agent(
    org: str,
    repo_name: str,
    branch_name: str,
    vulnerability_data: Dict[str, Any],
    workspace_dir: Path,
    log_dir: Path | None = None,
    auto_review: bool = True
) -> Dict[str, Any]:
    """
    Run the pull request agent to create and optionally review a PR.

    This agent is called AFTER the dependency-remediation-agent has:
    1. Created a fix branch
    2. Updated dependencies
    3. Committed changes
    4. Verified updates

    Args:
        org: GitHub organization name
        repo_name: Repository name
        branch_name: Fix branch name (e.g., fix/security-alerts-20260215)
        vulnerability_data: Original vulnerability object with CVE details
        workspace_dir: Working directory with clone
        log_dir: Optional directory for storing logs
        auto_review: Whether to run reviewer after creation

    Returns:
        {
            "status": "success" | "failure",
            "pr_url": str | None,
            "pr_number": int | None,
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
        log_dir = Path("logs") / f"pr_{repo_name}_{timestamp}"

    log_dir.mkdir(parents=True, exist_ok=True)
    transcript_file = log_dir / "transcript.txt"

    # System prompt for the orchestrator
    instructions = f"""
    You are a pull request orchestrator. Your job is to create and review pull requests
    for security updates.

    Use the 'memory' mcp server to track a list of TODOs for the PR workflow
    and update them as you complete each step.

    CONTEXT:
    - Organization: {org}
    - Repository: {repo_name}
    - Branch: {branch_name}
    - The dependency remediation agent has already created and committed changes

    WORKFLOW:

    1. PR CREATION (creator-agent):
       - Call the creator-agent to generate the PR
       - Provide vulnerability details for the PR description
       - Ensure proper formatting with actual newlines
       - Get the PR URL and number

    2. PR FIELD VALIDATION (reviewer-agent) - if auto_review enabled:
       - Call the reviewer-agent to evaluate the PR title and body
       - The reviewer will check completeness and correctness
       - If any fields are wrong it will update them directly via mcp__github__update_pull_request
       - The reviewer does NOT leave comments or reviews, it only updates PR fields

    IMPORTANT:
    - The fix branch ({branch_name}) already exists with committed changes
    - Use github-mcp to create the PR
    - PR body MUST use actual newlines, NOT escaped \\n
    - Include all CVE/GHSA identifiers from vulnerability data
    - Flag any major version updates prominently

    OUTPUT:
    After workflow completes, summarize:
    - PR URL
    - PR number
    - Review status (if applicable)
    """

    async def start_pr_workflow():
        yield {
            "type": "user",
            "message": {
                "role": "user",
                "content": f"""Create a pull request for the security updates:

Repository: {org}/{repo_name}
Branch: {branch_name}
Target: main

Use the vulnerability data to create a comprehensive PR description.
{"After creation, have the reviewer-agent evaluate the PR fields and update them directly if anything is wrong." if auto_review else ""}
"""
            }
        }

    result = {
        "status": "failure",
        "pr_url": None,
        "pr_number": None,
        "review_status": None,
        "duration_ms": 0,
        "error": None,
        "total_cost_usd": None
    }

    try:
        with TranscriptWriter(transcript_file) as transcript, \
             ObservabilityLogger(log_dir, transcript, agent_context="pull_request", workspace_dir=workspace_dir) as tool_logger:

            options = ClaudeAgentOptions(
                max_turns=500,
                permission_mode="acceptEdits",
                system_prompt=instructions,
                setting_sources=["project"],
                allowed_tools=PR_ORCHESTRATOR_APPROVED_TOOLS,
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

            transcript.write(f"=== PR Creation Started: {start_time.strftime('%Y%m%d_%H%M%S')} ===\n")
            transcript.write(f"Repository: {org}/{repo_name}\n")
            transcript.write(f"Branch: {branch_name}\n")
            transcript.write(f"Log directory: {log_dir}\n")
            transcript.write("=" * 60 + "\n\n")

            async with ClaudeSDKClient(options) as client:
                await client.query(start_pr_workflow())

                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                transcript.write(f"[ASSISTANT] {block.text}\n")
                                logging.debug(block.text)

                                # Extract PR URL
                                pr_match = re.search(
                                    r'https://github\.com/[^/]+/[^/]+/pull/(\d+)',
                                    block.text
                                )
                                if pr_match:
                                    result["pr_url"] = pr_match.group(0)
                                    result["pr_number"] = int(pr_match.group(1))

                                # Extract review status
                                if "APPROVED" in block.text.upper():
                                    result["review_status"] = "approved"
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
            transcript.write(f"=== PR Creation Completed: {end_time.strftime('%Y%m%d_%H%M%S')} ===\n")
            transcript.write(f"Status: {result['status']}\n")
            transcript.write(f"PR URL: {result['pr_url']}\n")
            transcript.write(f"Review: {result['review_status']}\n")
            transcript.write(f"Duration: {duration_ms}ms\n")

            logging.info(f"PR creation complete for {repo_name}: {result['status']}")

    except Exception as e:
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        result["duration_ms"] = duration_ms
        result["error"] = str(e)
        result["status"] = "failure"
        logging.error(f"PR creation failed for {repo_name}: {e}", exc_info=True)

    return result
