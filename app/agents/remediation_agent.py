"""
Remediation agent module for executing Claude agent with package-update-executor skill.
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
import json
import os

from app.mcp.github_mcp import get_github_mcp_config, get_github_mcp_tools
from app.utils.agentlogging import TranscriptWriter, ToolCallJsonlLogger
from app.mcp.jira_mcp import get_jira_mcp_config

APPROVED_TOOLS=[
    "Read", 
    "Grep", 
    "Bash", 
    "KillShell", 
    "BashOutput", 
    "Fetch", 
    "WebSearch", 
    "ExitPlanMode", 
    "SlashCommand", 
    "WebFetch",
    "Task", 
    "Glob", 
    "Grep", 
    "TodoWrite",
    "Skill",
    "MultiEdit"
] + get_github_mcp_tools()


async def run_remediation_agent(
    org: str,
    repository_data: Dict[str, Any],
    workspace_dir: Path,
    log_dir: Path | None = None
) -> Dict[str, Any]:
    """
    Run the Claude remediation agent for a single repository.
    
    Args:
        org: GitHub organization name
        repository_data: Repository security summary dictionary
        workspace_dir: Working directory for the agent (should contain vulnerability-object.json)
        log_dir: Optional directory for storing logs
    
    Returns:
        {
            "status": "success" | "failure",
            "repo_name": str,
            "pr_urls": List[str],
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
        log_dir = Path("logs") / f"agent_{repo_name}_{timestamp}"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    transcript_file = log_dir / "transcript.txt"
    
    # System prompt for the agent
    instructions = """
    You are an experienced software security expert. Your job is to remediate dependency vulnerabilities using the skill 'package-update-executor'.
    
    CRITICAL WORKFLOW REQUIREMENTS:
    
    1. REPOSITORY CONTEXT (Step 0 - REQUIRED FIRST STEP):
       - The vulnerability-object.json describes a REMOTE repository, NOT the local working directory
       - FIRST ACTION: Read vulnerability-object.json from the LOCAL orchestration directory
       - Extract: org, repository.name, repository.html_url
       - Target repository is: {org}/{repository.name} (e.g., AgentPOC-Org/python-uv-test)
    
    2. FILE ACCESS RULES (CRITICAL):
       - Use github-mcp tools (mcp__github__get_file_contents, mcp__github__search_code, etc.) for ALL target repository file access
       - NEVER use local file tools (Read, Grep, Bash find/cat/ls) to access dependency files
       - NEVER search the local filesystem for target repository files
       - Local working directory is ONLY for: vulnerability-object.json, orchestration scripts, and temporary workspace
    
    3. CORRECT FILE ACCESS PATTERN:
       ✅ DO: mcp__github__get_file_contents {org}/{repo-name}/uv.lock
       ✅ DO: mcp__github__get_file_contents {org}/{repo-name}/pyproject.toml
       ❌ DON'T: Read poetry.lock (this reads LOCAL file, not target repo)
       ❌ DON'T: Bash find . -name "*.lock" (searches LOCAL filesystem)
       ❌ DON'T: Grep "dependencies" uv.lock (accesses LOCAL file)
    
    4. SPARSE CLONE (Step 3):
       - Create sparse clone ONLY in a new workspace subdirectory (e.g., workspace/repo)
       - Clone the TARGET repository from vulnerability-object.json, not the orchestration directory
       - Use sparse checkout for minimal files only: manifest files + required companion files
    
    5. WORKFLOW STEPS:
       You MUST follow the package-update-executor skill workflow end-to-end:
       - Step 0: Validate Repository Context (read vulnerability-object.json)
       - Step 1: Parse alert payload
       - Step 2: Determine required files (via github-mcp)
       - Step 3: Minimal sparse clone in separate workspace
       - Step 4: Validate file presence
       - Step 5: Upgrade vulnerable dependencies
       - Step 6: Commit changes
       - Step 7: Create pull request
    
    6. TRACKING:
       - Use the 'memory' mcp server to track TODOs and project state
       - Track completion of each workflow step
    
    Remember: The local working directory (packagebot) contains orchestration code. The TARGET repository (from vulnerability-object.json) is accessed via github-mcp tools.
    """
    
    # User prompt for the agent
    async def perform_dependency_upgrade():
        yield {
            "type": "user",
            "message": {
                "role": "user",
                "content": "Perform a comprehensive and thorough remediation of the repository's dependencies. Don't spare an inch!"
            }
        }
    
    result = {
        "status": "failure",
        "repo_name": repo_name,
        "pr_urls": [],
        "duration_ms": 0,
        "error": None,
        "total_cost_usd": None,
        "num_turns": 0
    }
    
    try:
        # Initialize logging
        with TranscriptWriter(transcript_file) as transcript, \
             ToolCallJsonlLogger(log_dir) as tool_logger:
            
            # Create options with hooks
            options = ClaudeAgentOptions(
                max_turns=1000,
                permission_mode="acceptEdits",
                system_prompt=instructions,
                setting_sources=["project"],
                allowed_tools=APPROVED_TOOLS,
                mcp_servers={
                    "memory": {
                        "command": "npx",
                        "args": [
                            "-y",
                            "@modelcontextprotocol/server-memory"
                        ]
                    },
                    "github": get_github_mcp_config(),
                    "jira": get_jira_mcp_config()
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
            
            transcript.write(f"=== Agent Run Started: {start_time.strftime('%Y%m%d_%H%M%S')} ===\n")
            transcript.write(f"Repository: {repo_name}\n")
            transcript.write(f"Organization: {org}\n")
            transcript.write(f"Log directory: {log_dir}\n")
            transcript.write(f"Working directory: {workspace_dir}\n")
            transcript.write("=" * 60 + "\n\n")
            
            async with ClaudeSDKClient(options) as client:
                await client.query(perform_dependency_upgrade())
                
                pr_urls = []
                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                transcript.write(f"[ASSISTANT] {block.text}\n")
                                logging.debug(block.text)
                                
                                # Extract PR URLs from text
                                if "github.com" in block.text and "/pull/" in block.text:
                                    import re
                                    urls = re.findall(r'https://github\.com/[^/]+/[^/]+/pull/\d+', block.text)
                                    pr_urls.extend(urls)
                            
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
            
            # Deduplicate PR URLs
            result["pr_urls"] = list(set(pr_urls))
            
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            result["duration_ms"] = duration_ms
            
            transcript.write("\n" + "=" * 60 + "\n")
            transcript.write(f"=== Agent Run Completed: {end_time.strftime('%Y%m%d_%H%M%S')} ===\n")
            transcript.write(f"Status: {result['status']}\n")
            transcript.write(f"Duration: {duration_ms}ms\n")
            transcript.write(f"PR URLs: {result['pr_urls']}\n")
            
            logging.info(f"Agent run complete for {repo_name}: {result['status']}")
    
    except Exception as e:
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        result["duration_ms"] = duration_ms
        result["error"] = str(e)
        result["status"] = "failure"
        logging.error(f"Agent failed for {repo_name}: {e}", exc_info=True)
    
    return result