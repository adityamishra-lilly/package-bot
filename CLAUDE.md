# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Packagebot is an automated Dependabot alert remediation system that uses Claude AI agents orchestrated through Temporal workflows to automatically fix security vulnerabilities and create pull requests.

## Development Commands

```bash
# Install dependencies (root project)
poetry install

# Install Jira MCP server dependencies
cd jira-mcp && poetry install

# Start the Temporal worker (required for workflow execution)
python worker.py

# Linting and formatting
black .
ruff check .

# Run tests (root)
pytest

# Run Jira MCP tests
cd jira-mcp && poetry run pytest tests/unit/
```

## Architecture

### Workflow Hierarchy

```
PackagebotWorkflow (Parent - scheduled every Sunday 8PM)
├── DependabotAlertsWorkflow (Child - fetches and processes alerts)
│   ├── fetch_dependabot_alerts_activity → GitHub API
│   ├── build_alerts_object_activity → Creates remediation-plan.json
│   └── load_remediation_plan_activity → Extracts repository data
└── RemediationOrchestratorWorkflow (Child - per repository, sequential)
    ├── execute_dependency_remediation_activity
    │   └── DependencyRemediationAgent (planner → executor → verifier)
    └── execute_pull_request_activity
        └── PullRequestAgent (creator → reviewer)
```

### Two Separate Activities

The workflow executes two activities per repository in sequence:

1. **`execute_dependency_remediation_activity`** (`app/activities/`)
   - Calls `run_dependency_remediation_agent`
   - Creates branch, updates dependencies, commits changes
   - Returns: `branch_name`, `commit_hash`, `major_version_updates`, `workspace_dir`, `vulnerability_data`

2. **`execute_pull_request_activity`** (`app/activities/`)
   - Calls `run_pull_request_agent`
   - Creates and reviews PR from fix branch
   - Accepts data from remediation activity
   - Returns: `pr_url`, `pr_number`, `review_status`

### Agent Architecture

The system uses two main agents, each with specialized subagents:

#### 1. Dependency Remediation Agent (`app/agents/dependency-remediation/`)

Orchestrates vulnerability remediation with 3 subagents (all using `opus` model):

| Subagent | Purpose | Skill |
|----------|---------|-------|
| `planner-agent` | Analyzes vulnerabilities, detects major version updates, creates plan | `dependency-planner` |
| `executor-agent` | Performs sparse checkout, runs ecosystem-specific updates | `dependency-executor` |
| `verifier-agent` | Validates updates, checks lock files, confirms PR-readiness | `dependency-verifier` |

#### 2. Pull Request Agent (`app/agents/pull-request/`)

Handles PR creation separately from remediation:

| Subagent | Purpose | Skill |
|----------|---------|-------|
| `creator-agent` | Creates well-formatted PRs with CVE references | `pull-request-creator` |
| `reviewer-agent` | Reviews PRs for quality standards | `pull-request-reviewer` |

### Key Components

- **worker.py**: Entry point. Starts Temporal worker, registers workflows/activities
- **app/activities/execute_dependency_remediation_activity.py**: Wraps dependency remediation agent
- **app/activities/execute_pull_request_activity.py**: Wraps pull request agent
- **app/agents/remediation_agent.py**: `run_full_remediation()` - orchestrates both agents
- **app/agents/dependency-remediation/agent.py**: Main remediation orchestrator
- **app/agents/dependency-remediation/subagents/**: Planner, executor, verifier definitions
- **app/agents/pull-request/agent.py**: PR creation orchestrator
- **app/agents/pull-request/subagents/**: Creator, reviewer definitions
- **app/workflows/agent_orchestrator.py**: `RemediationOrchestratorWorkflow` - calls both activities

### MCP Servers

Three MCP servers provide tool access to agents:

| Server | Config Location | Transport | Purpose |
|--------|----------------|-----------|---------|
| GitHub | `app/mcp/github_mcp.py` | stdio (npx) | Repository access, PRs, file operations |
| Memory | Inline config | stdio (npx) | TODO tracking during agent execution |
| Jira | `app/mcp/jira_mcp.py` | stdio (poetry) | Ticket creation, search, workflow transitions |

#### Jira MCP Server (`jira-mcp/`)

Standalone FastMCP project providing 13 tools for Jira Cloud REST API v3:

```
jira-mcp/
├── src/jira_mcp/
│   ├── __main__.py          # Entry point: python -m jira_mcp
│   ├── server.py            # FastMCP("jira-mcp", lifespan=lifespan)
│   ├── settings.py          # JiraSettings(BaseSettings) - env-based config
│   ├── lifespan.py          # Creates/closes JiraClient on startup/shutdown
│   ├── jira/
│   │   ├── client.py        # Async httpx client wrapping Jira REST API v3
│   │   ├── models.py        # Pydantic response models
│   │   ├── adf.py           # Atlassian Document Format ↔ plain text helpers
│   │   └── errors.py        # JiraAPIError, JiraAuthError, JiraNotFoundError, etc.
│   ├── tools/
│   │   ├── issues.py        # create_issue, get_issue, update_issue, assign_issue, delete_issue
│   │   ├── search.py        # search_issues (JQL), get_issue_by_key
│   │   ├── comments.py      # add_comment, get_comments
│   │   ├── transitions.py   # get_transitions, transition_issue
│   │   └── projects.py      # list_projects, get_project
│   ├── guards/
│   │   ├── read_only.py     # Blocks writes when JIRA_READ_ONLY_MODE=true
│   │   ├── rate_limit.py    # Sliding-window rate limiter decorator
│   │   └── permissions.py   # READ_TOOLS / WRITE_TOOLS sets
│   ├── logging/logger.py    # Stderr logger (avoids stdio conflict)
│   └── utils/
│       ├── retry.py         # Exponential backoff for transient errors
│       └── timing.py        # @timed performance decorator
├── tests/
│   ├── unit/                # test_jira_client, test_tools_search, test_guards
│   └── integration/         # test_mcp_stdio (subprocess spawn test)
├── scripts/
│   ├── run_local.sh         # Load .env and start server
│   └── health_check.py      # Validate config + test Jira connectivity
└── docker/                  # Dockerfile + docker-compose.yml
```

**Agent integration** (same pattern as GitHub MCP):

```python
from app.mcp.jira_mcp import get_jira_mcp_config, get_jira_mcp_tools

mcp_servers={
    "jira": get_jira_mcp_config(),   # stdio subprocess
    "github": get_github_mcp_config(),
    "memory": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"]},
}
allowed_tools = [...] + get_jira_mcp_tools()  # mcp__jira__create_issue, etc.
```

**Key design decisions:**
- Tools accept plain text for descriptions/comments, convert to ADF internally
- All write tools call `check_read_only()` before executing
- All tools decorated with `@rate_limit` (sliding window, configurable)
- Logs to stderr to avoid corrupting stdio MCP transport
- Auth via Basic auth (email + API token) for Jira Cloud

### Skills Structure (`.claude/skills/`)

```
.claude/skills/
├── dependency-planner/
│   ├── SKILL.md
│   ├── scripts/          # analyze-vulnerabilities.sh, detect-ecosystem.sh, compare-versions.sh
│   └── references/       # ecosystem-detection.md, major-version-handling.md
├── dependency-executor/
│   ├── SKILL.md
│   ├── scripts/          # sparse-checkout.sh, update-pip.sh, update-npm.sh,
│   │                     # update-cargo.sh, update-go.sh, commit-changes.sh
│   └── references/       # sparse-checkout.md, update-commands.md
├── dependency-verifier/
│   ├── SKILL.md
│   ├── scripts/          # verify-versions.sh, validate-lockfile.sh,
│   │                     # verify-commit.sh, generate-report.sh
│   └── references/       # lockfile-formats.md, version-parsing.md
├── pull-request-creator/
│   ├── SKILL.md
│   ├── PR-template.md
│   └── templates/        # create-pr.sh, build-description.sh
└── pull-request-reviewer/
    ├── SKILL.md
    ├── scripts/          # review-pr.sh, check-diff.sh
    └── references/       # review-criteria.md
```

### Data Flow Between Activities

```
execute_dependency_remediation_activity
    │  Returns: branch_name, commit_hash, major_version_updates, workspace_dir, vulnerability_data
    ▼
execute_pull_request_activity
    │  Receives all above data, creates PR using branch_name
    │  Returns: pr_url, pr_number, review_status
    ▼
```

### Complete Data Flow

1. GitHub Dependabot API → raw alerts JSON
2. `build_alerts_object_activity` → `dependabot-remediation-plan/remediation-plan.json`
3. Per-repository: `execute_dependency_remediation_activity` creates `workspace/{repo}_{timestamp}/vulnerability-object.json`
4. **Planner**: Reads vulnerability-object.json, uses github-mcp to inspect remote repo, creates plan
5. **Executor**: Sparse checkout, runs update commands, commits changes
6. **Verifier**: Validates versions in lock files, confirms commit integrity
7. `execute_pull_request_activity` receives branch_name and vulnerability_data
8. **PR Creator**: Creates PR via github-mcp with proper formatting
9. **PR Reviewer**: Reviews PR quality (optional, controlled by `auto_review` flag)

## Vulnerability Object Structure

```json
{
  "org": "AgentPOC-Org",
  "repository": {
    "name": "repo-name",
    "html_url": "https://github.com/...",
    "security_alerts": [{
      "ecosystem": "pip|npm|go|cargo",
      "package": "package-name",
      "manifests": [{"path": "pyproject.toml", "scope": "runtime"}],
      "current_version": "1.2.3",
      "target_version": "2.0.0",
      "fix_versions": ["1.6.38", "2.0.0"],
      "severity": "critical|high|medium|low",
      "highest_cvss": 7.3,
      "ghsas": ["GHSA-..."],
      "cves": ["CVE-..."]
    }]
  }
}
```

## Environment Variables

Required in `.env`:
- `GITHUB_TOKEN` - GitHub API access for fetching alerts
- `GITHUB_COMMAND_TOKEN` - GitHub MCP server token for git operations
- `GITHUB_ORG` - Target organization name

Required for Jira MCP (in `.env` or passed via agent env):
- `JIRA_URL` - Jira instance URL (e.g. `https://yourteam.atlassian.net`)
- `JIRA_EMAIL` - Email for Jira API authentication
- `JIRA_API_TOKEN` - Jira API token

Optional:
- `TEMPORAL_HOST` - Defaults to localhost:7233
- `TEMPORAL_NAMESPACE` - Defaults to "default"
- `JIRA_READ_ONLY_MODE` - Block Jira writes (default: false)
- `JIRA_MAX_RESULTS` - Default search limit (default: 50)
- `JIRA_TIMEOUT` - HTTP timeout seconds (default: 30)
- `JIRA_RATE_LIMIT_CALLS` / `JIRA_RATE_LIMIT_PERIOD` - Rate limiting (default: 10/60s)
- `JIRA_LOG_LEVEL` - Logging level (default: INFO)

## Key Patterns

### Major Version Detection

The planner agent detects and flags major version updates:
- `1.x.x → 2.x.x` = MAJOR (breaking changes likely)
- `0.x.x → 1.x.x` = MAJOR (stability commitment)
- When flagged, planner checks for minor fix versions as alternatives

### Ecosystem-Specific Update Commands

| Ecosystem | Command |
|-----------|---------|
| Python (uv) | `uv lock --upgrade-package pkg==version` |
| Python (poetry) | `poetry update pkg@version --lock` |
| npm | `npm install pkg@version --package-lock-only` |
| yarn | `yarn add pkg@version --mode update-lockfile` |
| pnpm | `pnpm update pkg@version --lockfile-only` |
| cargo | `cargo update -p pkg@version` |
| go | `go get pkg@vversion && go mod tidy` |

### Sparse Checkout Pattern

```bash
git clone --no-checkout --filter=blob:none {repo_url} repo
cd repo
git checkout -b fix/security-alerts-$(date +%Y%m%d-%H%M%S)
git sparse-checkout init --no-cone
git sparse-checkout set pyproject.toml uv.lock
git checkout
```

### Agent Configuration

All subagents use:
- Model: `opus`
- Memory MCP server for TODO tracking
- GitHub MCP for repository access
- Jira MCP for ticket management
- Skills from `.claude/skills/`

### Temporal Workflows

- Task queue: `packagebot-task-queue`
- Activity timeouts:
  - Dependency remediation: 15min (with heartbeat)
  - Pull request: 5min (with heartbeat)
- Retry policy:
  - Remediation: 3 attempts with exponential backoff
  - PR creation: 2 attempts
- Repositories processed sequentially to avoid rate limiting

### Agent Execution

- Max turns: 1000 (remediation), 500 (PR)
- Permission mode: `acceptEdits`
- MCP servers: GitHub, Memory, Jira
- Logs: `logs/{agent_type}_{repo}_{timestamp}/`
- Workspace: `workspace/{repo}_{timestamp}/`

## Critical Rules

1. **Remote vs Local**: Target repo files accessed via github-mcp, NOT local filesystem
2. **Sparse Checkout**: Only checkout required manifest and lock files
3. **Lock-Only Updates**: Use `--package-lock-only` flags to avoid full installs
4. **PR Body Formatting**: Use actual newlines, NOT escaped `\n`
5. **Major Versions**: Flag prominently, prefer minor fixes when available
6. **Separate Activities**: Remediation and PR creation are separate activities with data passing
7. **Data Passing**: branch_name, vulnerability_data, workspace_dir flow from remediation to PR activity
8. **Jira MCP Logging**: Always log to stderr, never stdout (stdio transport)
9. **ADF Conversion**: Tools accept plain text; conversion to Atlassian Document Format is internal
10. **Read-Only Mode**: Set `JIRA_READ_ONLY_MODE=true` to prevent accidental Jira writes during testing
