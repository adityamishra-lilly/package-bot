# jira-mcp

A Jira MCP (Model Context Protocol) server for Claude AI agents. Enables ticket creation, search, commenting, and workflow transitions via stdio transport.

## Setup

```bash
cd jira-mcp
poetry install
```

### Configuration

Copy `.env.example` to `.env` and fill in your Jira credentials:

```bash
cp .env.example .env
```

Required environment variables:

| Variable | Description |
|----------|-------------|
| `JIRA_URL` | Your Jira instance URL (e.g. `https://yourteam.atlassian.net`) |
| `JIRA_EMAIL` | Email for Jira API authentication |
| `JIRA_API_TOKEN` | [Jira API token](https://id.atlassian.com/manage-profile/security/api-tokens) |

Optional:

| Variable | Default | Description |
|----------|---------|-------------|
| `JIRA_READ_ONLY_MODE` | `false` | Block all write operations |
| `JIRA_MAX_RESULTS` | `50` | Default max results for searches |
| `JIRA_TIMEOUT` | `30` | HTTP request timeout (seconds) |
| `JIRA_RATE_LIMIT_CALLS` | `10` | Max API calls per period |
| `JIRA_RATE_LIMIT_PERIOD` | `60` | Rate limit window (seconds) |
| `JIRA_LOG_LEVEL` | `INFO` | Logging level |

### Health Check

```bash
poetry run python scripts/health_check.py
```

## Running

```bash
# Direct
poetry run python -m jira_mcp

# Via script (loads .env automatically)
bash scripts/run_local.sh
```

## Usage with Claude Agents

Configure as an MCP server in your agent's `mcp_servers`:

```python
mcp_servers={
    "jira": {
        "command": "poetry",
        "args": ["run", "python", "-m", "jira_mcp"],
        "env": {
            "JIRA_URL": jira_url,
            "JIRA_EMAIL": jira_email,
            "JIRA_API_TOKEN": jira_api_token,
        },
        "cwd": "/path/to/jira-mcp"
    }
}
```

Tools are then available as `mcp__jira__<tool_name>`.

## Available Tools (13)

### Issues
- **`create_issue`** - Create a new issue (project_key, summary, issue_type, description, priority, labels)
- **`get_issue`** - Get issue by key
- **`update_issue`** - Update issue fields
- **`assign_issue`** - Assign/unassign an issue
- **`delete_issue`** - Delete an issue

### Search
- **`search_issues`** - Search with JQL query
- **`get_issue_by_key`** - Get issue by key (alias)

### Comments
- **`add_comment`** - Add a plain text comment
- **`get_comments`** - Get all comments on an issue

### Transitions
- **`get_transitions`** - List available workflow transitions
- **`transition_issue`** - Move issue to a new status

### Projects
- **`list_projects`** - List accessible projects
- **`get_project`** - Get project details

## JQL Examples

```
# All open bugs in a project
project = PROJ AND issuetype = Bug AND status != Done

# High priority issues assigned to me
assignee = currentUser() AND priority in (High, Highest) AND status != Done

# Issues updated in the last 7 days
project = PROJ AND updated >= -7d

# Security-related issues
project = PROJ AND labels = security AND status = "To Do"
```

## Testing

```bash
# Unit tests
poetry run pytest tests/unit/

# Integration test (spawns server subprocess)
poetry run pytest tests/integration/ -m integration

# All tests
poetry run pytest
```

## Docker

```bash
cd docker
docker-compose up --build
```

## Architecture

```
src/jira_mcp/
├── __init__.py          # Package exports
├── __main__.py          # Entry point (python -m jira_mcp)
├── server.py            # FastMCP instance
├── settings.py          # Pydantic settings from env
├── lifespan.py          # Startup/shutdown lifecycle
├── jira/
│   ├── client.py        # Async httpx Jira REST API v3 client
│   ├── models.py        # Pydantic response models
│   ├── adf.py           # Atlassian Document Format helpers
│   └── errors.py        # Exception hierarchy
├── tools/
│   ├── issues.py        # CRUD tools for issues
│   ├── search.py        # JQL search tools
│   ├── comments.py      # Comment tools
│   ├── transitions.py   # Workflow transition tools
│   └── projects.py      # Project listing tools
├── guards/
│   ├── read_only.py     # Write-blocking guard
│   ├── rate_limit.py    # Sliding-window rate limiter
│   └── permissions.py   # Tool permission sets
├── logging/
│   └── logger.py        # Stderr logger (avoids stdio conflict)
└── utils/
    ├── retry.py         # Exponential backoff retry
    └── timing.py        # Performance timing decorator
```
