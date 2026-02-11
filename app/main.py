from claude_agent_sdk import (
    ClaudeSDKClient, 
    ThinkingBlock,
    ClaudeAgentOptions, 
    AssistantMessage, 
    TextBlock,
    HookMatcher,
)
import logging
from dotenv import load_dotenv
import os
import asyncio
from pathlib import Path
from datetime import datetime
from app.mcp.github_mcp import get_github_mcp_config, get_github_mcp_tools
from app.utils.agentlogging import TranscriptWriter, ToolCallJsonlLogger
from app.mcp.jira_mcp import get_jira_mcp_config

load_dotenv()

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



async def upgrade_the_dependencies():
    # Setup logging directories
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path("logs") / f"run_{timestamp}"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    transcript_file = log_dir / "transcript.txt"
    
    #system prompt
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
    # user prompt section
    async def perform_dependency_upgrade():
        yield {
            "type": "user",
            "message": {
                "role": "user",
                "content": "Perform a comprehensive and thorough remediation of the repository's dependencies. Don't spare an inch!"
            }
        }

    # Initialize logging
    with TranscriptWriter(transcript_file) as transcript, \
         ToolCallJsonlLogger(log_dir) as tool_logger:
        
        # Create options with hooks included in constructor
        options = ClaudeAgentOptions(
            max_turns = 1000,
            permission_mode="acceptEdits",
            system_prompt=instructions,
            setting_sources=["project"],
            allowed_tools = APPROVED_TOOLS,
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
            cwd = os.getcwd(),
        )
        
        transcript.write(f"=== Agent Run Started: {timestamp} ===\n")
        transcript.write(f"Log directory: {log_dir}\n")
        transcript.write(f"Transcript: {transcript_file}\n")
        transcript.write(f"Tool calls: {log_dir / 'tool_calls.jsonl'}\n")
        transcript.write("=" * 60 + "\n\n")

        async with ClaudeSDKClient(options) as client:
            await client.query(perform_dependency_upgrade())

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            transcript.write(f"[ASSISTANT] {block.text}\n")
                            logging.info(block.text)
                        if isinstance(block, ThinkingBlock):
                            transcript.write(f"[THINKING] {block.thinking}\n")
                            logging.info(block.thinking)
        
        transcript.write("\n" + "=" * 60 + "\n")
        transcript.write(f"=== Agent Run Completed: {datetime.now().strftime('%Y%m%d_%H%M%S')} ===\n")
        
        print(f"\n✅ Agent run complete. Logs saved to: {log_dir}")


if __name__ == "__main__":
    asyncio.run(upgrade_the_dependencies())