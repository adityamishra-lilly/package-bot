# Packagebot Flow Diagram

## Complete Workflow Chain

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TEMPORAL SCHEDULE                                   │
│                     Cron: "0 20 * * 0" (Sunday 8PM)                        │
│                                                                             │
│  Input: { workflow_id, org, state, enable_remediation }                     │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PackagebotWorkflow                                   │
│                        (Parent Workflow)                                    │
│                                                                             │
│  Step 1: DependabotAlertsWorkflow (child)                                  │
│  Step 2: For each repo → RemediationOrchestratorWorkflow (child)           │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
          ┌─────────────────┐         ┌──────────────────────────┐
          │ DependabotAlerts │         │ RemediationOrchestrator  │
          │ Workflow (1x)    │         │ Workflow (1 per repo)    │
          └────────┬────────┘         └────────────┬─────────────┘
                   │                               │
          3 Activities                    3 Activities per repo
          (sequential)                    (sequential)
```

---

## Step 1: DependabotAlertsWorkflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DependabotAlertsWorkflow                               │
│                                                                             │
│  Input: { workflow_id, org, state, severities, per_page }                  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Activity 1: fetch_dependabot_alerts_activity                        │  │
│  │                                                                       │  │
│  │  Input:  { org, state, per_page, severities }                        │  │
│  │  Action: GET /orgs/{org}/dependabot/alerts (paginated)               │  │
│  │  Output: { alerts: [...], count: 42 }                                │  │
│  └──────────────────────────────┬────────────────────────────────────────┘  │
│                                 │ raw alerts JSON                           │
│                                 ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Activity 2: build_alerts_object_activity                            │  │
│  │                                                                       │  │
│  │  Input:  { org, raw_alerts: [...] }                                  │  │
│  │  Action: Groups alerts by (repo, ecosystem, package)                 │  │
│  │          Extracts CVEs, GHSAs, CVSS, fix versions                    │  │
│  │          Writes remediation-plan.json to disk                        │  │
│  │  Output: { file_path, status, repo_count, alert_count }             │  │
│  └──────────────────────────────┬────────────────────────────────────────┘  │
│                                 │ file path                                 │
│                                 ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Activity 3: load_remediation_plan_activity                          │  │
│  │                                                                       │  │
│  │  Input:  { remediation_plan_path }                                   │  │
│  │  Action: Reads JSON file, extracts repository list                   │  │
│  │  Output: { status, repositories: [...] }                             │  │
│  └──────────────────────────────┬────────────────────────────────────────┘  │
│                                 │                                           │
│  Output: { repositories, fetch_result, build_result, load_result }         │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  │ repositories: [
                                  │   { name, html_url, security_alerts: [...] },
                                  │   { name, html_url, security_alerts: [...] },
                                  │   ...
                                  │ ]
                                  ▼
                    PackagebotWorkflow loops over each repo
                    and spawns a child workflow per repository
```

---

## Step 2: RemediationOrchestratorWorkflow (per repository)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               RemediationOrchestratorWorkflow                               │
│               (one instance per repository)                                 │
│                                                                             │
│  Input: {                                                                  │
│    org: "AgentPOC-Org",                                                    │
│    repository: { name, html_url, security_alerts: [...] },                 │
│    auto_review: true                                                       │
│  }                                                                         │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Activity 1: execute_dependency_remediation_activity                  │  │
│  │  Timeout: 30 min | Retries: 3                                        │  │
│  │                                                                       │  │
│  │  Payload: { org, repository }                                        │  │
│  │                                                                       │  │
│  │  Returns: {                                                          │  │
│  │    status, repo_name, branch_name, commit_hash,                      │  │
│  │    major_version_updates, packages_updated,                          │  │
│  │    verification_status, workspace_dir, vulnerability_data,           │  │
│  │    duration_ms, total_cost_usd, num_turns                            │  │
│  │  }                                                                   │  │
│  └──────────────────────────────┬────────────────────────────────────────┘  │
│            (if success)         │ branch_name, vulnerability_data,          │
│                                 │ workspace_dir, major_version_updates      │
│                                 ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Activity 2: execute_pull_request_activity                           │  │
│  │  Timeout: 30 min | Retries: 2                                        │  │
│  │                                                                       │  │
│  │  Payload: {                                                          │  │
│  │    org, repo_name, branch_name, vulnerability_data,                  │  │
│  │    workspace_dir, major_version_updates, auto_review                 │  │
│  │  }                                                                   │  │
│  │                                                                       │  │
│  │  Returns: {                                                          │  │
│  │    status, pr_url, pr_number, review_status,                         │  │
│  │    duration_ms, total_cost_usd                                       │  │
│  │  }                                                                   │  │
│  └──────────────────────────────┬────────────────────────────────────────┘  │
│           (if PR success)       │ pr_url, pr_number                         │
│                                 ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Activity 3: execute_jira_ticket_activity  (NON-CRITICAL)            │  │
│  │  Timeout: 30 min | Retries: 2                                        │  │
│  │                                                                       │  │
│  │  Payload: {                                                          │  │
│  │    org, repo_name, pr_url, pr_number, branch_name,                   │  │
│  │    vulnerability_data, workspace_dir, major_version_updates          │  │
│  │  }                                                                   │  │
│  │                                                                       │  │
│  │  Returns: {                                                          │  │
│  │    status, jira_key, jira_url, review_status,                        │  │
│  │    duration_ms, total_cost_usd                                       │  │
│  │  }                                                                   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Output: {                                                                 │
│    repo_name, status, pr_url, pr_number, branch_name,                      │
│    major_version_updates, remediation_duration_ms, pr_duration_ms,         │
│    jira_key, jira_url, jira_duration_ms, error, total_cost_usd            │
│  }                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Activity 1 Detail: execute_dependency_remediation_activity

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              execute_dependency_remediation_activity                         │
│                                                                             │
│  Receives: { org, repository }                                             │
│                                                                             │
│  Pre-work (Python):                                                        │
│    1. Creates workspace dir: workspace/{repo}_{timestamp}/                 │
│    2. Creates log dir: logs/remediation_{repo}_{timestamp}/                │
│    3. Writes vulnerability-object.json to workspace                        │
│                                                                             │
│  Then calls: run_dependency_remediation_agent()                            │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │           DependencyRemediationAgent (Orchestrator)                   │  │
│  │                                                                       │  │
│  │  Model: opus | Max turns: 1000                                       │  │
│  │  MCP: github, memory                                                 │  │
│  │  Tools: Read, Grep, Bash, Write, Glob, TodoWrite, Skill, Task,      │  │
│  │         MultiEdit + all github mcp tools                             │  │
│  │  CWD: workspace/{repo}_{timestamp}/                                  │  │
│  │                                                                       │  │
│  │  Receives from system prompt:                                        │  │
│  │    - Instructions for 3-phase workflow                               │  │
│  │    - vulnerability-object.json in CWD                                │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Phase 1: planner-agent (subagent)                             │  │  │
│  │  │                                                                 │  │  │
│  │  │  Model: opus                                                   │  │  │
│  │  │  Skill: dependency-planner                                     │  │  │
│  │  │  Tools: Read, Grep, Glob, WebFetch, WebSearch, TodoWrite,     │  │  │
│  │  │         Skill + read-only github mcp tools                     │  │  │
│  │  │                                                                 │  │  │
│  │  │  What it does:                                                 │  │  │
│  │  │    1. Reads vulnerability-object.json from workspace           │  │  │
│  │  │    2. Inspects target repo files via github MCP                │  │  │
│  │  │       (pyproject.toml, go.mod, package.json, etc.)             │  │  │
│  │  │    3. Identifies ecosystems (pip/uv/npm/cargo/go)              │  │  │
│  │  │    4. Detects MAJOR version updates (1.x→2.x, 0.x→1.x)       │  │  │
│  │  │    5. Checks for minor fix_version alternatives                │  │  │
│  │  │    6. Determines files needed for sparse checkout              │  │  │
│  │  │    7. Creates update commands per ecosystem                    │  │  │
│  │  │                                                                 │  │  │
│  │  │  Output: Structured update plan with:                          │  │  │
│  │  │    - Repo analysis (ecosystems, vuln count)                    │  │  │
│  │  │    - Per-package plan (current→target, CVEs, severity)         │  │  │
│  │  │    - [MAJOR_VERSION_UPDATE] flags                              │  │  │
│  │  │    - Files to checkout list                                    │  │  │
│  │  │    - Ecosystem-specific update commands                        │  │  │
│  │  │    - Verification steps                                        │  │  │
│  │  └─────────────────────────────────┬───────────────────────────────┘  │  │
│  │                                    │ plan                              │  │
│  │                                    ▼                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Phase 2: executor-agent (subagent)                            │  │  │
│  │  │                                                                 │  │  │
│  │  │  Model: opus                                                   │  │  │
│  │  │  Skill: dependency-executor                                    │  │  │
│  │  │  Tools: Read, Bash, Write, MultiEdit, Glob, Grep,             │  │  │
│  │  │         TodoWrite, Skill                                       │  │  │
│  │  │                                                                 │  │  │
│  │  │  What it does:                                                 │  │  │
│  │  │    1. Creates clone/ subdirectory in workspace                 │  │  │
│  │  │    2. git clone --no-checkout --filter=blob:none {repo_url}    │  │  │
│  │  │    3. git checkout -b fix/security-alerts-{timestamp}          │  │  │
│  │  │    4. git sparse-checkout set {manifest} {lockfile}            │  │  │
│  │  │    5. Runs ecosystem-specific update commands:                 │  │  │
│  │  │       - uv lock --upgrade-package pkg==ver                     │  │  │
│  │  │       - npm install pkg@ver --package-lock-only                │  │  │
│  │  │       - go get pkg@vver && go mod tidy                         │  │  │
│  │  │       - cargo update -p pkg@ver                                │  │  │
│  │  │    6. git add + git commit with CVE references                 │  │  │
│  │  │                                                                 │  │  │
│  │  │  Output:                                                       │  │  │
│  │  │    - Branch name: fix/security-alerts-YYYYMMDD-HHMMSS         │  │  │
│  │  │    - Commit hash                                               │  │  │
│  │  │    - Files modified list                                       │  │  │
│  │  │    - Commands executed + status                                │  │  │
│  │  └─────────────────────────────────┬───────────────────────────────┘  │  │
│  │                                    │ branch, commit, files             │  │
│  │                                    ▼                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Phase 3: verifier-agent (subagent)                            │  │  │
│  │  │                                                                 │  │  │
│  │  │  Model: opus                                                   │  │  │
│  │  │  Skill: dependency-verifier                                    │  │  │
│  │  │  Tools: Read, Bash, Grep, Glob, TodoWrite, Skill              │  │  │
│  │  │                                                                 │  │  │
│  │  │  What it does:                                                 │  │  │
│  │  │    1. Parses updated lock files for resolved versions          │  │  │
│  │  │    2. Confirms each package is at target version               │  │  │
│  │  │    3. Validates only expected files were modified               │  │  │
│  │  │    4. Checks lock file format integrity                        │  │  │
│  │  │    5. Verifies commit message follows conventions              │  │  │
│  │  │    6. Checks major version updates are documented              │  │  │
│  │  │    7. Confirms branch is ready for PR                          │  │  │
│  │  │                                                                 │  │  │
│  │  │  Output: Verification report with:                             │  │  │
│  │  │    - Status: SUCCESS / FAILURE / PARTIAL                       │  │  │
│  │  │    - Per-package version verification table                    │  │  │
│  │  │    - Major version update verification                         │  │  │
│  │  │    - Files checked + status                                    │  │  │
│  │  │    - Ready for PR: YES / NO                                    │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                       │  │
│  │  Final output extracted by orchestrator via regex:                    │  │
│  │    - branch_name (fix/security-alerts-XXXXXXXX-XXXXXX)               │  │
│  │    - commit_hash                                                      │  │
│  │    - major_version_updates list                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Returns: {                                                                │
│    status, repo_name, branch_name, commit_hash, major_version_updates,     │
│    packages_updated, verification_status, workspace_dir,                   │
│    vulnerability_data, duration_ms, total_cost_usd, num_turns              │
│  }                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Activity 2 Detail: execute_pull_request_activity

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              execute_pull_request_activity                                   │
│                                                                             │
│  Receives: {                                                               │
│    org, repo_name, branch_name, vulnerability_data,                        │
│    workspace_dir, major_version_updates, auto_review                       │
│  }                                                                         │
│                                                                             │
│  Pre-work (Python):                                                        │
│    1. Resolves workspace_dir (or creates new one)                          │
│    2. Creates log dir: logs/pr_{repo}_{timestamp}/                         │
│                                                                             │
│  Then calls: run_pull_request_agent()                                      │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │           PullRequestAgent (Orchestrator)                             │  │
│  │                                                                       │  │
│  │  Model: opus | Max turns: 500                                        │  │
│  │  MCP: github, memory                                                 │  │
│  │  Tools: Read, Grep, Bash, Glob, TodoWrite, Skill, Task              │  │
│  │         + all github mcp tools                                       │  │
│  │  CWD: workspace/{repo}_{timestamp}/                                  │  │
│  │                                                                       │  │
│  │  Receives from system prompt:                                        │  │
│  │    - org, repo_name, branch_name                                     │  │
│  │    - Instructions for 2-phase workflow                               │  │
│  │                                                                       │  │
│  │  Receives as user message:                                           │  │
│  │    - Repository, branch, target info                                 │  │
│  │    - Whether to run reviewer                                         │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Phase 1: creator-agent (subagent)                             │  │  │
│  │  │                                                                 │  │  │
│  │  │  Model: opus                                                   │  │  │
│  │  │  Skill: pull-request-creator                                   │  │  │
│  │  │  Tools: Read, Bash, Grep, Glob, TodoWrite, Skill              │  │  │
│  │  │         + all github mcp tools                                 │  │  │
│  │  │                                                                 │  │  │
│  │  │  What it does:                                                 │  │  │
│  │  │    1. Reads verification report from remediation                │  │  │
│  │  │    2. Gathers vulnerability details (CVEs, severity, versions) │  │  │
│  │  │    3. Builds PR description with:                              │  │  │
│  │  │       - Vulnerability table (Package|From|To|CVE|Severity)     │  │  │
│  │  │       - Changes made section                                   │  │  │
│  │  │       - Major version warnings (if any)                        │  │  │
│  │  │       - Files modified list                                    │  │  │
│  │  │       - Co-Authored-By attribution                             │  │  │
│  │  │    4. Creates PR via mcp__github__create_pull_request          │  │  │
│  │  │       (head: fix branch, base: main)                           │  │  │
│  │  │                                                                 │  │  │
│  │  │  Output: PR URL, PR number, title, status                     │  │  │
│  │  └─────────────────────────────────┬───────────────────────────────┘  │  │
│  │                                    │ PR URL, PR number                 │  │
│  │                                    ▼                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Phase 2: reviewer-agent (subagent)  [if auto_review=true]     │  │  │
│  │  │                                                                 │  │  │
│  │  │  Model: opus                                                   │  │  │
│  │  │  Skill: pull-request-reviewer                                  │  │  │
│  │  │  Tools: Read, Bash, Grep, Glob, WebFetch, TodoWrite, Skill    │  │  │
│  │  │         + all github mcp tools                                 │  │  │
│  │  │                                                                 │  │  │
│  │  │  What it does:                                                 │  │  │
│  │  │    1. Fetches PR details via github MCP                        │  │  │
│  │  │    2. Checks description quality:                              │  │  │
│  │  │       - Clear security title                                   │  │  │
│  │  │       - Vulnerability table present                            │  │  │
│  │  │       - CVE/GHSA identifiers included                         │  │  │
│  │  │       - Major version warnings (if applicable)                 │  │  │
│  │  │    3. Validates code changes:                                  │  │  │
│  │  │       - Only lock files modified                               │  │  │
│  │  │       - No sensitive files                                     │  │  │
│  │  │    4. Provides APPROVED / CHANGES_REQUESTED / PENDING          │  │  │
│  │  │                                                                 │  │  │
│  │  │  Output: Review report with checklist + recommendation         │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                       │  │
│  │  Final output extracted by orchestrator via regex:                    │  │
│  │    - PR URL (https://github.com/org/repo/pull/N)                     │  │
│  │    - PR number                                                        │  │
│  │    - Review status (approved / changes_requested)                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Returns: {                                                                │
│    status, pr_url, pr_number, review_status,                               │
│    duration_ms, total_cost_usd                                             │
│  }                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Activity 3 Detail: execute_jira_ticket_activity

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              execute_jira_ticket_activity (NON-CRITICAL)                     │
│                                                                             │
│  Receives: {                                                               │
│    org, repo_name, pr_url, pr_number, branch_name,                         │
│    vulnerability_data, workspace_dir, major_version_updates,               │
│    project_key (optional)                                                  │
│  }                                                                         │
│                                                                             │
│  Pre-work (Python):                                                        │
│    1. Resolves workspace_dir (or creates new one)                          │
│    2. Creates log dir: logs/jira_{repo}_{timestamp}/                       │
│                                                                             │
│  Then calls: run_jira_ticket_agent()                                       │
│                                                                             │
│  Pre-work in agent.py (Python, before LLM):                               │
│    1. Computes highest severity from vulnerability_data                    │
│    2. Maps severity → Jira priority (critical→Highest, high→High, etc.)   │
│    3. Counts severity totals (critical: N, high: N, ...)                   │
│    4. Formats vulnerability summary for user message                       │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │           JiraTicketAgent (Orchestrator)                               │  │
│  │                                                                       │  │
│  │  Model: opus | Max turns: 500                                        │  │
│  │  MCP: jira, github, memory                                           │  │
│  │  Tools: Read, Grep, Bash, Glob, TodoWrite, Skill, Task              │  │
│  │         + all jira mcp tools + all github mcp tools                  │  │
│  │  CWD: workspace/{repo}_{timestamp}/                                  │  │
│  │                                                                       │  │
│  │  Receives from system prompt:                                        │  │
│  │    - org, repo_name, pr_url, pr_number, branch_name                  │  │
│  │    - Pre-computed: highest_severity, jira_priority, severity_counts   │  │
│  │    - Major version updates list (if any)                             │  │
│  │    - project_key (if provided)                                       │  │
│  │                                                                       │  │
│  │  Receives as user message:                                           │  │
│  │    - PR URL, PR number, repo info                                    │  │
│  │    - Formatted vulnerability summary (per-package details)           │  │
│  │    - Priority and label instructions                                 │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Phase 1: creator-agent (subagent)                             │  │  │
│  │  │                                                                 │  │  │
│  │  │  Model: opus                                                   │  │  │
│  │  │  Skill: jira-ticket-creator                                    │  │  │
│  │  │  Tools: Read, Bash, Grep, Glob, TodoWrite, Skill              │  │  │
│  │  │         + all jira mcp tools                                   │  │  │
│  │  │                                                                 │  │  │
│  │  │  What it does:                                                 │  │  │
│  │  │    1. Builds issue description (plain text):                   │  │  │
│  │  │       - PR link                                                │  │  │
│  │  │       - Vulnerability table (Pkg|From|To|CVE|Severity|CVSS)   │  │  │
│  │  │       - Severity summary counts                                │  │  │
│  │  │       - Major version warnings (if any)                        │  │  │
│  │  │       - Action items checklist                                 │  │  │
│  │  │    2. Creates Bug issue via mcp__jira__create_issue:           │  │  │
│  │  │       - project_key: from config                               │  │  │
│  │  │       - issue_type: "Bug"                                      │  │  │
│  │  │       - summary: "Review PR #N: Security dependency            │  │  │
│  │  │                   updates for {repo}"                          │  │  │
│  │  │       - priority: pre-computed from severity                   │  │  │
│  │  │       - labels: ["security", "dependabot", "automated"]        │  │  │
│  │  │       - description: plain text (Jira MCP → ADF)              │  │  │
│  │  │                                                                 │  │  │
│  │  │  Output: Jira key (PROJ-456), URL                             │  │  │
│  │  └─────────────────────────────────┬───────────────────────────────┘  │  │
│  │                                    │ jira_key, jira_url               │  │
│  │                                    ▼                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Phase 2: reviewer-agent (subagent)                            │  │  │
│  │  │                                                                 │  │  │
│  │  │  Model: opus                                                   │  │  │
│  │  │  Skill: jira-ticket-reviewer                                   │  │  │
│  │  │  Tools: Read, Bash, Grep, Glob, WebFetch, TodoWrite, Skill    │  │  │
│  │  │         + all jira mcp tools                                   │  │  │
│  │  │                                                                 │  │  │
│  │  │  What it does:                                                 │  │  │
│  │  │    1. Fetches ticket via mcp__jira__get_issue                  │  │  │
│  │  │    2. Validates against checklist:                              │  │  │
│  │  │       - Summary format correct                                 │  │  │
│  │  │       - PR link present                                        │  │  │
│  │  │       - Vulnerability table complete                           │  │  │
│  │  │       - CVE/GHSA refs included                                │  │  │
│  │  │       - Priority matches severity                              │  │  │
│  │  │       - Labels correct                                         │  │  │
│  │  │       - Major version warnings (if applicable)                 │  │  │
│  │  │    3. Self-corrects via mcp__jira__update_issue if needed      │  │  │
│  │  │       (fix labels, priority, description)                      │  │  │
│  │  │                                                                 │  │  │
│  │  │  Output: APPROVED / FIXED / CHANGES_REQUESTED                  │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                       │  │
│  │  Final output extracted by orchestrator via regex:                    │  │
│  │    - Jira key (PROJ-456)                                              │  │
│  │    - Jira URL (https://team.atlassian.net/browse/PROJ-456)           │  │
│  │    - Review status (approved / fixed / changes_requested)             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Returns: {                                                                │
│    status, jira_key, jira_url, review_status,                              │
│    duration_ms, total_cost_usd                                             │
│  }                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## MCP Server Access by Agent

```
                        ┌──────────┐  ┌──────────┐  ┌──────────┐
                        │  GitHub   │  │   Jira   │  │  Memory  │
                        │   MCP     │  │   MCP    │  │   MCP    │
                        └────┬─────┘  └────┬─────┘  └────┬─────┘
                             │             │              │
  DependencyRemediation ─────●─────────────┼──────────────●
    planner-agent ───────────● (read-only) ┼──────────────●
    executor-agent ──────────┼─────────────┼──────────────●
    verifier-agent ──────────┼─────────────┼──────────────●
                             │             │              │
  PullRequestAgent ──────────●─────────────┼──────────────●
    creator-agent ───────────●─────────────┼──────────────●
    reviewer-agent ──────────●─────────────┼──────────────●
                             │             │              │
  JiraTicketAgent ───────────●─────────────●──────────────●
    creator-agent ───────────┼─────────────●──────────────●
    reviewer-agent ──────────┼─────────────●──────────────●

  ● = has access    ┼ = no access
```

---

## End-to-End Data Flow Summary

```
GitHub Dependabot API
  │
  │  GET /orgs/{org}/dependabot/alerts
  ▼
Raw alerts JSON (paginated)
  │
  │  Group by (repo, ecosystem, package)
  │  Extract CVEs, GHSAs, CVSS, fix versions
  ▼
remediation-plan.json
  │
  │  Extract repository list
  ▼
repositories: [ {name, html_url, security_alerts}, ... ]
  │
  │  For each repository (one child workflow each):
  ▼
┌─ vulnerability-object.json written to workspace/{repo}_{ts}/
│
├─ Planner reads vuln JSON + inspects remote repo via GitHub MCP
│  → Update plan with commands, files, major version flags
│
├─ Executor does sparse checkout + runs update commands + commits
│  → branch_name, commit_hash
│
├─ Verifier validates lock files, versions, commit integrity
│  → verification report
│
├─ PR Creator builds description + creates PR via GitHub MCP
│  → pr_url, pr_number
│
├─ PR Reviewer validates PR quality
│  → APPROVED / CHANGES_REQUESTED
│
├─ Jira Creator maps severity→priority + creates Bug via Jira MCP
│  → jira_key, jira_url
│
└─ Jira Reviewer validates ticket + self-corrects if needed
   → APPROVED / FIXED / CHANGES_REQUESTED
```
