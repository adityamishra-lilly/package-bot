# PackageBot - AI-Powered Dependency Security Remediation Agent

## Overview

**PackageBot** is an automated AI agent that remediates security vulnerabilities in software dependencies by:
- Reading Dependabot-style vulnerability alerts from JSON payloads
- Performing minimal, targeted package updates to fix security issues
- Creating pull requests with comprehensive documentation via GitHub integration
- Supporting multiple package ecosystems (Python, Node.js, Rust, etc.)

The agent uses Claude Agent SDK with Model Context Protocol (MCP) servers to orchestrate the entire remediation workflow autonomously.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     PackageBot Agent                     │
│                                                          │
│  ┌────────────┐      ┌──────────────────────────┐      │
│  │  main.py   │─────▶│  Claude Agent SDK        │      │
│  │  (entry)   │      │  - Max 10,000 turns      │      │
│  └────────────┘      │  - Auto-approve edits    │      │
│                      │  - System instructions   │      │
│                      └──────────────────────────┘      │
│                                ▲                         │
│                                │                         │
│  ┌─────────────────────────────┼─────────────────────┐  │
│  │         MCP Servers         │                     │  │
│  │  ┌──────────────┐  ┌────────┴────────┐          │  │
│  │  │   GitHub     │  │     Memory      │          │  │
│  │  │   - Clone    │  │  - TODO Track   │          │  │
│  │  │   - Branch   │  │  - State Mgmt   │          │  │
│  │  │   - Commit   │  │                 │          │  │
│  │  │   - PR       │  └─────────────────┘          │  │
│  │  └──────────────┘                                │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Data Models (Pydantic)                   │  │
│  │  - OrgSecuritySummary                            │  │
│  │  - RepositorySecuritySummary                     │  │
│  │  - SecurityAlertSummary                          │  │
│  │  - SecurityAlertRef                              │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Activities                          │  │
│  │  - fetch_dependabot_alerts.py                    │  │
│  │  - build__alerts_object.py                       │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## File Structure

### Core Files

| File | Purpose |
|------|---------|
| **`main.py`** | Entry point that orchestrates the remediation agent using Claude Agent SDK. Configures MCP servers (GitHub, Memory), sets system instructions, and manages the agent lifecycle. |
| **`models.py`** | Pydantic data models defining the structure of security alerts, repository summaries, and vulnerability metadata. |
| **`github_mcp.py`** | Helper module to configure GitHub MCP server with authenticated access using `GIT_COMMAND_TOKEN` environment variable. |
| **`vulnerability-object.json`** | Example Dependabot-compatible alert payload containing repository vulnerabilities, affected packages, and remediation metadata. |
| **`pyproject.toml`** | Poetry project configuration with dependencies: `claude-agent-sdk`, `requests`, `python-dotenv`. |
| **`poetry.lock`** | Locked dependency versions for reproducible builds. |
| **`.env`** | Environment configuration (gitignored - contains `GIT_COMMAND_TOKEN` and `GITHUB_TOKEN`). |
| **`.gitignore`** | Excludes virtual environments, cache files, and environment variables. |

### Activities Directory

| File | Purpose |
|------|---------|
| **`fetch_dependabot_alerts.py`** | Fetches organization-wide Dependabot alerts from GitHub API with RFC5988 Link header pagination support. Returns raw alert data. |
| **`build__alerts_object.py`** | Transforms raw GitHub alerts into structured `OrgSecuritySummary` objects. Groups alerts by repository and package, extracts metadata (CVEs, GHSAs, CVSS scores), and writes remediation plan JSON. |

### Skill Definition (.claude/skills/package-update-executor/)

| File | Purpose |
|------|---------|
| **`scripts/SKILL.md`** | Complete skill definition for dependency security remediation. Documents the 7-step workflow, ecosystem support (uv, poetry, npm, cargo), and minimal sparse clone strategy. |
| **`references/PR-template.md`** | Markdown template for automated pull requests. Includes severity tables, affected dependencies, security advisory details, and change summaries. |

---

## Workflow: 7-Step Remediation Process

The agent follows this deterministic workflow defined in the `package-update-executor` skill:

### 1. **Parse Alert Payload**
- Read `vulnerability-object.json`
- Extract: repository, ecosystem, package, manifests, target versions
- Identify highest safe version from `fix_versions[]`

### 2. **Determine Required Files**
- Identify minimal file set based on ecosystem:
  - **Python (uv)**: `uv.lock` + `pyproject.toml`
  - **Python (poetry)**: `poetry.lock` + `pyproject.toml`
  - **Node.js**: `package.json` + `package-lock.json`/`yarn.lock`/`pnpm-lock.yaml`
  - **Rust**: `Cargo.toml` + `Cargo.lock`
- Use GitHub MCP search to locate companion files if needed

### 3. **Minimal Sparse Clone**
```bash
git clone --no-checkout --filter=blob:none <repo_url> repo
cd repo
git checkout -b <branch_name>
git sparse-checkout init --no-cone
git sparse-checkout set <required_files>
git checkout
```

### 4. **Validate File Presence**
- Verify all required files exist
- Abort if missing with logged failure reason

### 5. **Upgrade Vulnerable Dependencies**
- **Python (uv)**: `uv lock --upgrade-package <package>==<version>`
- **Node.js**: `npm install <package>@<version> --package-lock-only`
- **Rust**: `cargo update -p <package>:<version>`
- Only modify lock files, avoid full installs

### 6. **Commit Changes**
```bash
git add <modified_files>
git commit -m "chore(deps): fix security alerts for <packages>"
```

### 7. **Create Pull Request**
- Use GitHub MCP to create PR with detailed template
- Include vulnerability details, severity, CVEs, and affected versions

---

## Data Models

### OrgSecuritySummary
Top-level organization security summary containing:
- Organization name
- Source (e.g., `github_dependabot_org_alerts`)
- Alert state (`open`/`closed`)
- List of `RepositorySecuritySummary` objects

### RepositorySecuritySummary
Per-repository summary containing:
- Repository name and HTML URL
- List of `SecurityAlertSummary` objects

### SecurityAlertSummary
Package-level vulnerability aggregation:
- Ecosystem (`pip`, `npm`, `cargo`)
- Package name
- Manifest references with scope
- Current/target versions
- Fix versions list
- Severity and CVSS score
- GHSAs and CVEs
- Vulnerable version ranges
- Summary and references
- List of `SecurityAlertRef` objects

### SecurityAlertRef
Individual alert metadata:
- Alert number and HTML URL
- Alert-specific summary (truncated)
- Per-alert GHSAs/CVEs
- Severity level
- Vulnerable version range

---

## Supported Ecosystems

| Ecosystem | Package Manager | Manifest | Lock File(s) |
|-----------|----------------|----------|--------------|
| Python (uv) | `uv` | `pyproject.toml` | `uv.lock` |
| Python (poetry) | `poetry` | `pyproject.toml` | `poetry.lock` |
| Node.js | `npm` | `package.json` | `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml` |
| Rust | `cargo` | `Cargo.toml` | `Cargo.lock` |

---

## Configuration

### Environment Variables

Create a `.env` file with:
```bash
GIT_COMMAND_TOKEN=ghp_xxxxxxxxxxxx  # GitHub Personal Access Token
GITHUB_TOKEN=ghp_xxxxxxxxxxxx       # GitHub API token (for fetching alerts)
```

### Required Permissions

GitHub token needs:
- `repo` - Full repository access
- `security_events` - Read security alerts
- `workflow` - Create/update workflows

### MCP Servers

Configured in `main.py`:

1. **GitHub MCP** (`@modelcontextprotocol/server-github`)
   - Tools: create_branch, create_or_update_file, push_files, create_pull_request
   - Authenticated with `GIT_COMMAND_TOKEN`

2. **Memory MCP** (`@modelcontextprotocol/server-memory`)
   - Tracks TODO items and project state
   - Maintains context across workflow steps

---

## Usage

### 1. Install Dependencies
```bash
poetry install
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your GitHub tokens
```

### 3. Prepare Vulnerability Data
Place Dependabot alert JSON in `vulnerability-object.json` or fetch via:
```python
from activities.fetch_dependabot_alerts import fetch_dependabot_alerts
alerts = await fetch_dependabot_alerts(org="your-org", state="open")
```

### 4. Run Remediation Agent
```bash
poetry run python main.py
```

The agent will:
- Read vulnerability alerts
- Execute the 7-step remediation workflow
- Create a PR with fixes in the target repository

---

## Example Vulnerability Object

```json
{
  "org": "AgentPOC-Org",
  "source": "github_dependabot_org_alerts",
  "state": "open",
  "repository": {
    "name": "python-uv-test",
    "html_url": "https://github.com/AgentPOC-Org/python-uv-test",
    "security_alerts": [
      {
        "ecosystem": "pip",
        "package": "virtualenv",
        "manifests": [{"path": "uv.lock", "scope": "runtime"}],
        "target_version": "20.36.1",
        "severity": "medium",
        "ghsas": ["GHSA-597g-3phw-6986"],
        "cves": ["CVE-2026-22702"]
      }
    ]
  }
}
```

---

## Agent Features

### Intelligence
- **Autonomous Decision Making**: Uses Claude Agent SDK for multi-turn reasoning
- **Comprehensive Auditing**: Analyzes entire dependency tree
- **Skill-Based Execution**: Follows structured `package-update-executor` skill workflow
- **State Management**: Tracks progress via Memory MCP server

### Safety
- **Minimal Changes**: Only updates vulnerable packages, no formatting changes
- **Sparse Cloning**: Downloads only required files
- **Lock-Only Updates**: No full dependency installations
- **Version Validation**: Uses explicit fix versions from advisories

### Automation
- **GitHub Integration**: End-to-end PR creation
- **Multi-Ecosystem**: Supports Python, Node.js, Rust
- **Pagination Handling**: Fetches all org alerts (RFC5988 compliant)
- **Rich Metadata**: Includes CVEs, GHSAs, CVSS scores in PRs

---

## Project Dependencies

### Runtime
- **claude-agent-sdk** (0.1.33) - AI agent orchestration
- **requests** (2.32.5) - HTTP client for GitHub API
- **python-dotenv** (1.2.1) - Environment variable management

### Development
- **pytest** (9.0.2) - Testing framework
- **black** (26.1.0) - Code formatting
- **ruff** (0.15.0) - Linting and code quality

---

## Future Enhancements

Potential improvements based on architecture:

1. **Multi-Repository Processing**: Batch remediation across org repos
2. **Test Automation**: Validate PRs with CI/CD integration
3. **Custom Policies**: Org-specific upgrade strategies
4. **Rollback Support**: Automatic reversion on failed checks
5. **Metrics Dashboard**: Track remediation success rates
6. **Notification System**: Alert security teams of critical issues

---

## License

Not specified in repository.

## Contributing

The project uses Poetry for dependency management and follows Python best practices with Black formatting and Ruff linting.

---

**Generated**: 2026-02-08  
**Repository**: c:\Users\L108186\poc\packagebot