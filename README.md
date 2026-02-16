# Packagebot

Automated Dependabot alert remediation system that uses Claude AI agents orchestrated through Temporal workflows to fix security vulnerabilities, create pull requests, and track them with Jira tickets.

## How It Works

Packagebot runs on a weekly schedule (Sundays at 8 PM). It fetches open Dependabot alerts across an entire GitHub organization, groups them by repository, and for each repository:

1. Plans dependency updates based on vulnerability data
2. Performs sparse checkouts and runs lock-file-only updates
3. Verifies the updates succeeded
4. Creates a pull request with a detailed vulnerability summary
5. Reviews the PR for quality
6. Creates a Jira Bug ticket to track human review of the PR

The entire pipeline is autonomous. Human intervention is only needed at the end: reviewing the PR and merging it.

## Architecture

```
                           Temporal Schedule (Sunday 8PM)
                                      |
                              PackagebotWorkflow
                                      |
                         DependabotAlertsWorkflow
                          /           |           \
                 fetch alerts   build plan    load repos
                                      |
                    RemediationOrchestratorWorkflow
                         (per repository, sequential)
                          /           |           \
                   Remediation       PR          Jira
                    Activity      Activity      Activity
                       |             |             |
                   3 subagents    2 subagents   2 subagents
```

### Workflow Hierarchy

| Workflow | Role |
|----------|------|
| `PackagebotWorkflow` | Parent. Scheduled entry point. Launches child workflows. |
| `DependabotAlertsWorkflow` | Child. Fetches alerts from GitHub API, builds remediation plan JSON, extracts repository list. |
| `RemediationOrchestratorWorkflow` | Child. Processes each repository sequentially through three activities. |

### Activities

The orchestrator executes three activities per repository in sequence:

| # | Activity | Timeout | Retries | Agent |
|---|----------|---------|---------|-------|
| 1 | `execute_dependency_remediation_activity` | 30 min | 3 | DependencyRemediationAgent |
| 2 | `execute_pull_request_activity` | 30 min | 2 | PullRequestAgent |
| 3 | `execute_jira_ticket_activity` | 30 min | 2 | JiraTicketAgent |

Activity 3 (Jira) is **non-critical** -- if it fails, the repository result still counts as successful because the PR (the primary deliverable) was created.

### Agent Architecture

Each agent is an orchestrator that delegates to specialized subagents:

```
DependencyRemediationAgent
  |-- planner-agent     Analyzes vulnerabilities, detects major versions, creates plan
  |-- executor-agent    Sparse checkout, runs ecosystem-specific update commands
  \-- verifier-agent    Validates versions in lock files, confirms commit integrity

PullRequestAgent
  |-- creator-agent     Creates PR via GitHub MCP with vulnerability table
  \-- reviewer-agent    Reviews PR against quality checklist

JiraTicketAgent
  |-- creator-agent     Creates Bug issue via Jira MCP with PR link and severity
  \-- reviewer-agent    Validates ticket quality, self-corrects via update_issue
```

All subagents use the `opus` model and have access to MCP servers for tool use.

### MCP Servers

Agents interact with external services through Model Context Protocol servers:

| Server | Transport | Purpose | Used By |
|--------|-----------|---------|---------|
| GitHub | stdio (`npx @modelcontextprotocol/server-github`) | Repository access, PRs, file operations | Remediation, PR, Jira agents |
| Jira | stdio (`poetry run python -m jira_mcp`) | Issue CRUD, search, transitions | Jira agent |
| Memory | stdio (`npx @modelcontextprotocol/server-memory`) | TODO tracking during agent execution | All agents |

## Data Flow

```
GitHub Dependabot API
        |
        v
fetch_dependabot_alerts_activity        Raw alerts JSON (paginated)
        |
        v
build_alerts_object_activity            dependabot-remediation-plan/remediation-plan.json
        |
        v
load_remediation_plan_activity          List of repositories with security_alerts
        |
        v  (per repository)
execute_dependency_remediation_activity
  |  Planner reads vulnerability-object.json, inspects remote repo via GitHub MCP
  |  Executor does sparse checkout, runs update commands, commits
  |  Verifier validates lock files, confirms versions
  |
  |  Returns: branch_name, commit_hash, vulnerability_data,
  |           major_version_updates, workspace_dir
  v
execute_pull_request_activity
  |  Creator builds PR description with vulnerability table, creates PR
  |  Reviewer validates PR quality, approves or requests changes
  |
  |  Returns: pr_url, pr_number, review_status
  v
execute_jira_ticket_activity
  |  Creator maps highest severity to Jira priority, creates Bug issue
  |  Reviewer validates ticket completeness, self-corrects if needed
  |
  |  Returns: jira_key, jira_url, review_status
  v
Done. Human reviews the PR and Jira ticket.
```

## Vulnerability Object Structure

Each repository's alerts are normalized into this format:

```json
{
  "org": "AgentPOC-Org",
  "repository": {
    "name": "repo-name",
    "html_url": "https://github.com/...",
    "security_alerts": [
      {
        "ecosystem": "pip",
        "package": "virtualenv",
        "manifests": [{"path": "pyproject.toml", "scope": "runtime"}],
        "current_version": "20.0.0",
        "target_version": "20.28.1",
        "fix_versions": ["20.28.1"],
        "severity": "medium",
        "highest_cvss": 5.3,
        "ghsas": ["GHSA-..."],
        "cves": ["CVE-2025-68146"]
      }
    ]
  }
}
```

## Ecosystem Support

| Ecosystem | Manifest | Lock File | Update Command |
|-----------|----------|-----------|----------------|
| Python (uv) | pyproject.toml | uv.lock | `uv lock --upgrade-package pkg==version` |
| Python (poetry) | pyproject.toml | poetry.lock | `poetry update pkg@version --lock` |
| npm | package.json | package-lock.json | `npm install pkg@version --package-lock-only` |
| yarn | package.json | yarn.lock | `yarn add pkg@version --mode update-lockfile` |
| pnpm | package.json | pnpm-lock.yaml | `pnpm update pkg@version --lockfile-only` |
| Cargo | Cargo.toml | Cargo.lock | `cargo update -p pkg@version` |
| Go | go.mod | go.sum | `go get pkg@vversion && go mod tidy` |

All updates are **lock-file-only** -- no full installs are performed. Only manifest and lock files are checked out via sparse checkout.

## Major Version Detection

The planner detects and flags major version updates:

| Current | Target | Classification |
|---------|--------|----------------|
| 1.x.x | 2.x.x | MAJOR -- breaking changes likely |
| 0.x.x | 1.x.x | MAJOR -- stability commitment |
| 1.2.x | 1.3.x | MINOR |
| 1.2.3 | 1.2.4 | PATCH |

When a major version is detected, the planner checks for minor fix versions as alternatives and flags the update prominently in the PR and Jira ticket.

## Project Structure

```
packagebot/
|-- worker.py                           Entry point. Temporal worker + schedule
|-- app/
|   |-- config.py                       Environment-based configuration
|   |-- workflows/
|   |   |-- workflow.py                 PackagebotWorkflow, DependabotAlertsWorkflow
|   |   \-- agent_orchestrator.py       RemediationOrchestratorWorkflow
|   |-- activities/
|   |   |-- fetch_dependabot_alerts.py  GitHub API alert fetching
|   |   |-- build__alerts_object.py     Alert grouping + remediation plan JSON
|   |   |-- load_remediation_plan.py    Load repositories from plan file
|   |   |-- execute_dependency_remediation_activity.py
|   |   |-- execute_pull_request_activity.py
|   |   \-- execute_jira_ticket_activity.py
|   |-- agents/
|   |   |-- remediation_agent.py        run_full_remediation() orchestrator
|   |   |-- dependency_remediation/     Planner, executor, verifier subagents
|   |   |-- pull_request/              Creator, reviewer subagents
|   |   \-- jira_ticket/               Creator, reviewer subagents
|   |-- mcp/
|   |   |-- github_mcp.py              GitHub MCP config + tool allowlist
|   |   \-- jira_mcp.py                Jira MCP config + tool allowlist
|   |-- services/
|   |   \-- temporal_client.py          Temporal client singleton
|   \-- utils/
|       |-- app_logging.py             Application logger
|       \-- agentlogging.py            TranscriptWriter, ToolCallJsonlLogger
|-- jira-mcp/                           Standalone Jira MCP server (FastMCP)
|   |-- src/jira_mcp/
|   |   |-- server.py                  FastMCP server definition
|   |   |-- settings.py               Pydantic-based env config
|   |   |-- lifespan.py               JiraClient lifecycle
|   |   |-- jira/                      Client, models, ADF helpers, errors
|   |   |-- tools/                     13 Jira tools (issues, search, comments, transitions, projects)
|   |   |-- guards/                    Read-only mode, rate limiting, permissions
|   |   \-- logging/                   Stderr logger (avoids stdio conflict)
|   |-- tests/
|   \-- scripts/
|-- .claude/skills/                     Agent skill definitions
|   |-- dependency-planner/
|   |-- dependency-executor/
|   |-- dependency-verifier/
|   |-- pull-request-creator/
|   |-- pull-request-reviewer/
|   |-- jira-ticket-creator/
|   \-- jira-ticket-reviewer/
\-- dependabot-remediation-plan/        Generated remediation plan output
```

## Setup

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/)
- [Temporal server](https://docs.temporal.io/cli) running locally or remotely
- Node.js (for `npx`-based MCP servers)

### Installation

```bash
# Install project dependencies
poetry install

# Install Jira MCP server dependencies
cd jira-mcp && poetry install && cd ..
```

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required
GITHUB_TOKEN=ghp_...              # GitHub API access for fetching alerts
GIT_COMMAND_TOKEN=ghp_...         # GitHub MCP server token for git operations
GITHUB_ORG=YourOrg                # Target GitHub organization

# Required for Jira integration
JIRA_URL=https://yourteam.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=ATATT3x...

# Optional
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=default
JIRA_READ_ONLY_MODE=false         # Block Jira writes during testing
JIRA_MAX_RESULTS=50
JIRA_TIMEOUT=30
JIRA_RATE_LIMIT_CALLS=10
JIRA_RATE_LIMIT_PERIOD=60
JIRA_LOG_LEVEL=INFO
```

Also create `jira-mcp/.env` with the same Jira credentials (or copy from `.env.example`).

### Running

```bash
# Start the Temporal worker (registers workflows, activities, and schedule)
python worker.py
```

The worker registers a Temporal schedule that triggers `PackagebotWorkflow` every Sunday at 8 PM. You can also trigger workflows manually via the Temporal UI or CLI.

## Development

```bash
# Formatting
black .

# Linting
ruff check .

# Tests
pytest

# Jira MCP tests
cd jira-mcp && poetry run pytest tests/unit/
```

## Key Design Decisions

- **Lock-file-only updates**: No full installs. Uses `--package-lock-only` and equivalent flags to minimize side effects.
- **Sparse checkout**: Only manifest and lock files are checked out, keeping clones minimal.
- **Sequential processing**: Repositories are processed one at a time to avoid GitHub API rate limiting.
- **Non-critical Jira**: Jira ticket creation failure doesn't fail the overall workflow. The PR is the primary deliverable.
- **Severity-to-priority mapping**: Python code pre-computes Jira priority from the highest severity, reducing LLM guesswork.
- **Plain text Jira descriptions**: The Jira MCP accepts plain text and converts to Atlassian Document Format internally.
- **Separate activities**: Remediation, PR creation, and Jira ticket creation are independent Temporal activities with their own retry policies and timeouts.
- **Cost tracking**: Each agent reports `total_cost_usd` which is aggregated up through the workflow.
