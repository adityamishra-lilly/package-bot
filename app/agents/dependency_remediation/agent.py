"""
Dependency Remediation Agent - Main orchestration module.

This agent orchestrates three subagents to remediate dependency vulnerabilities:
1. Planner - Analyzes vulnerabilities and creates update plan
2. Executor - Performs sparse checkout and updates
3. Verifier - Validates updates were successful

Note: PR creation is handled by a separate pull-request-agent.
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
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import re

from app.mcp.github_mcp import get_github_mcp_config, get_github_mcp_tools
from app.utils.agentlogging import TranscriptWriter, ObservabilityLogger

from .subagents import (
    planner_agent,
    executor_agent,
    verifier_agent,
)

# Tools available to the main orchestrator
ORCHESTRATOR_APPROVED_TOOLS = [
    "Read",
    "Grep",
    "Bash",
    "Write",
    "Glob",
    "TodoWrite",
    "Skill",
    "Task",
    "MultiEdit",
] + get_github_mcp_tools()


async def run_dependency_remediation_agent(
    org: str,
    repository_data: Dict[str, Any],
    workspace_dir: Path,
    log_dir: Path | None = None
) -> Dict[str, Any]:
    """
    Run the dependency remediation agent for a single repository.

    This agent orchestrates three subagents:
    1. planner-agent: Analyzes vulnerabilities and creates update plan
    2. executor-agent: Performs sparse checkout and updates
    3. verifier-agent: Validates updates were successful

    Note: Does NOT create PRs - that's handled by pull-request-agent.

    Args:
        org: GitHub organization name
        repository_data: Repository security summary dictionary
        workspace_dir: Working directory (should contain vulnerability-object.json)
        log_dir: Optional directory for storing logs

    Returns:
        {
            "status": "success" | "failure" | "partial",
            "repo_name": str,
            "branch_name": str | None,
            "commit_hash": str | None,
            "major_version_updates": List[str],
            "packages_updated": List[Dict],
            "verification_status": str,
            "duration_ms": int,
            "error": None | str,
            "total_cost_usd": float | None,
            "num_turns": int
        }
    """
    repo_name = repository_data.get("name", "unknown")
    start_time = datetime.now()

    # Create log directory if not provided
    if log_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path("logs") / f"remediation_{repo_name}_{timestamp}"

    log_dir.mkdir(parents=True, exist_ok=True)
    transcript_file = log_dir / "transcript.txt"

    # System prompt for the orchestrator
    instructions = """
    You are a dependency remediation orchestrator. Your job is to coordinate three subagents
    to remediate security vulnerabilities in a repository's dependencies.

    Use the 'memory' mcp server to track a list of TODOs based on the vulnerabilities found
    and update the TODOs as you progress through each phase.

    WORKFLOW:

    1. PLANNING PHASE (planner-agent):
       - Call the planner-agent to analyze vulnerability-object.json
       - The planner will identify ecosystems, required files, and update commands
       - The planner outputs a structured plan following the template in
         .claude/skills/dependency-planner/templates/remediation-plan-template.md
       - The plan is automatically saved to `remediation-plan.md` in the workspace
       - Pay attention to MAJOR_VERSION_UPDATE flags - these need careful handling
       - Review the plan before proceeding

    2. EXECUTION PHASE (executor-agent):
       - Call the executor-agent to perform the updates
       - The executor reads `remediation-plan.md` as its first step (this is automatic)
       - It uses Section 3 (Files to Checkout), Section 4 (Update Commands), and
         Section 5 (Commit and Push Instructions) from the plan
       - The executor MUST run update commands via Bash — it must NOT manually edit files
       - The executor commits and pushes with `git commit` + `git push`
       - Monitor for any errors during execution
       - Note the branch name and commit hash

    3. VERIFICATION PHASE (verifier-agent):
       - Call the verifier-agent to validate the updates
       - The verifier can reference Section 6 (Verification Checklist) from the plan
       - Ensure all packages are at expected versions
       - Verify major version updates are properly documented
       - Confirm the branch is pushed and ready for PR creation

    IMPORTANT RULES:
    - vulnerability-object.json is in your current working directory
    - Target repository files are accessed via github-mcp, NOT local filesystem
    - Create sparse clone in a subdirectory, not current directory
    - DO NOT create pull requests - that's handled separately
    - If any phase fails, report the failure and stop
    - The planner's output is saved to remediation-plan.md automatically
    - The planner MUST produce the complete 7-section plan (not a summary)
    - The executor MUST run update commands via Bash, NEVER manually edit files
    - The executor pushes with git push after committing

    OUTPUT:
    After all phases complete, summarize:
    - Packages updated (with version changes)
    - Major version updates detected
    - Branch name and commit hash
    - Verification status
    - Any warnings or issues
    """

    async def start_remediation():
        yield {
            "type": "user",
            "message": {
                "role": "user",
                "content": """Execute the dependency remediation workflow:
1. Use planner-agent to analyze vulnerabilities and create update plan
2. Use executor-agent to perform the updates
3. Use verifier-agent to validate the results

Report the final status including branch name, commit hash, and any major version updates."""
            }
        }

    result = {
        "status": "failure",
        "repo_name": repo_name,
        "branch_name": None,
        "commit_hash": None,
        "major_version_updates": [],
        "packages_updated": [],
        "verification_status": "not_run",
        "duration_ms": 0,
        "error": None,
        "total_cost_usd": None,
        "num_turns": 0
    }

    try:
        with TranscriptWriter(transcript_file) as transcript, \
             ObservabilityLogger(log_dir, transcript, agent_context="remediation", workspace_dir=workspace_dir) as tool_logger:

            options = ClaudeAgentOptions(
                max_turns=1000,
                permission_mode="acceptEdits",
                system_prompt=instructions,
                setting_sources=["project"],
                allowed_tools=ORCHESTRATOR_APPROVED_TOOLS,
                agents={
                    "planner-agent": planner_agent,
                    "executor-agent": executor_agent,
                    "verifier-agent": verifier_agent,
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

            transcript.write(f"=== Dependency Remediation Started: {start_time.strftime('%Y%m%d_%H%M%S')} ===\n")
            transcript.write(f"Repository: {repo_name}\n")
            transcript.write(f"Organization: {org}\n")
            transcript.write(f"Log directory: {log_dir}\n")
            transcript.write(f"Working directory: {workspace_dir}\n")
            transcript.write("=" * 60 + "\n\n")

            async with ClaudeSDKClient(options) as client:
                await client.query(start_remediation())

                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                transcript.write(f"[ASSISTANT] {block.text}\n")
                                logging.debug(block.text)

                                # Extract branch name
                                if "fix/security-alerts" in block.text:
                                    branch_match = re.search(r'(fix/security-alerts-\d{8}-\d{6})', block.text)
                                    if branch_match:
                                        result["branch_name"] = branch_match.group(1)

                                # Extract commit hash
                                commit_match = re.search(r'Commit:\s*([a-f0-9]{7,40})', block.text)
                                if commit_match:
                                    result["commit_hash"] = commit_match.group(1)

                                # Check for major version updates
                                if "MAJOR_VERSION_UPDATE" in block.text:
                                    major_matches = re.findall(r'\[MAJOR_VERSION_UPDATE\]\s*(\S+)', block.text)
                                    result["major_version_updates"].extend(major_matches)

                            if isinstance(block, ThinkingBlock):
                                transcript.write(f"[THINKING] {block.thinking}\n")
                                logging.debug(block.thinking)

                    # Check for ResultMessage
                    if hasattr(message, 'subtype'):
                        if message.subtype == "success":
                            result["status"] = "success"
                            result["total_cost_usd"] = getattr(message, 'total_cost_usd', None)
                            result["num_turns"] = getattr(message, 'num_turns', 0)
                        elif message.subtype == "error":
                            result["status"] = "failure"
                            result["error"] = getattr(message, 'result', "Unknown error")

            # Deduplicate major version updates
            result["major_version_updates"] = list(set(result["major_version_updates"]))

            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            result["duration_ms"] = duration_ms

            transcript.write("\n" + "=" * 60 + "\n")
            transcript.write(f"=== Remediation Completed: {end_time.strftime('%Y%m%d_%H%M%S')} ===\n")
            transcript.write(f"Status: {result['status']}\n")
            transcript.write(f"Branch: {result['branch_name']}\n")
            transcript.write(f"Commit: {result['commit_hash']}\n")
            transcript.write(f"Major Updates: {result['major_version_updates']}\n")
            transcript.write(f"Duration: {duration_ms}ms\n")

            logging.info(f"Remediation complete for {repo_name}: {result['status']}")

    except Exception as e:
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        result["duration_ms"] = duration_ms
        result["error"] = str(e)
        result["status"] = "failure"
        logging.error(f"Remediation failed for {repo_name}: {e}", exc_info=True)

    return result
