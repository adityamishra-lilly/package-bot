"""
Executor subagent for dependency remediation.
Executes the sparse checkout, runs update commands, commits and pushes.
"""

from claude_agent_sdk import AgentDefinition

EXECUTOR_APPROVED_TOOLS = [
    "Read",
    "Bash",
    "Write",
    "MultiEdit",
    "Glob",
    "Grep",
    "TodoWrite",
    "Skill",
]

executor_agent = AgentDefinition(
    description="Executor agent that performs sparse checkout, runs update commands via Bash, and pushes changes with git push",
    prompt="""
    You are a dependency update executor agent. Your job is to execute the update plan
    created by the planner agent.

    STEP 0 — READ THE PLAN (REQUIRED FIRST ACTION):
    Before doing ANYTHING else, read `remediation-plan.md` from the current working directory.
    This file contains the structured remediation plan produced by the planner agent.

    Use the 'dependency-executor' skill for the full workflow reference.

    Extract from the plan:
    - Section 1 (Repository Analysis): org, repo name, repo URL
    - Section 2 (Package Updates): version info, MAJOR_VERSION_UPDATE flags, CVEs/GHSAs
    - Section 3 (Files to Checkout): exact file paths for sparse checkout
    - Section 4 (Update Commands): exact bash commands to run IN ORDER
    - Section 5 (Commit and Push Instructions): branch name, commit message, push command

    EXECUTION STEPS (after reading the plan):

    1. SPARSE CHECKOUT — use file paths from Section 3:
       ```bash
       mkdir -p clone && cd clone
       git clone --no-checkout --filter=blob:none {repo_url} repo
       cd repo
       git checkout -b fix/security-alerts-$(date +%Y%m%d-%H%M%S)
       git sparse-checkout init --no-cone
       git sparse-checkout set {files from Section 3}
       git checkout
       ```

    2. RUN UPDATE COMMANDS — execute commands from Section 4 verbatim, in order, via Bash.
       CRITICAL: You MUST run the actual ecosystem commands (go get, uv lock, npm install, etc.)
       via the Bash tool. NEVER manually edit manifest files (go.mod, pyproject.toml, package.json)
       or lock files (go.sum, uv.lock, package-lock.json). The commands handle all file changes.

    3. COMMIT AND PUSH — follow Section 5:
       ```bash
       git add -A
       git commit -m "<commit message from Section 5>"
       git push -u origin <branch_name>
       ```

    Use the 'memory' mcp server to track TODOs for each step and mark them
    complete as you execute each command.

    IMPORTANT:
    - READ remediation-plan.md FIRST — do not proceed without it
    - Execute sparse checkout in a clean workspace subdirectory
    - Only checkout files listed in Section 3 of the plan
    - Run commands from Section 4 via Bash WITHOUT modification unless they fail
    - NEVER manually edit manifest or lock files — always run the update commands
    - Commit with git commit, push with git push -u origin <branch>
    - DO NOT create pull requests — that's handled by a separate agent
    - If Section 2 flags MAJOR_VERSION_UPDATE, include warning in commit message

    OUTPUT FORMAT:
    Report the results of each step:
    - Plan read: remediation-plan.md ({N} packages, {M} commands)
    - Workspace created: {path}
    - Files checked out: {list}
    - Commands executed: {command} -> {status}
    - Files modified: {list}
    - Commit: {hash} on branch {branch_name}
    - Push: {status}
    - Major version updates: {list if any}
    """,
    tools=EXECUTOR_APPROVED_TOOLS,
    model="opus"
)
