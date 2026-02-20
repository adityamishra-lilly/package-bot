---
name: dependency-planner
description: Analyzes vulnerability data and creates a detailed dependency update plan. Use when you need to plan updates for security vulnerabilities, identify ecosystems, determine required files, and detect major version changes.
allowed-tools: Read, Grep, Glob, WebFetch, WebSearch, TodoWrite, mcp__github__get_file_contents, mcp__github__search_code, mcp__github__search_repositories, mcp__github__list_commits, mcp__github__search_issues, mcp__github__list_issues
---

# Dependency Update Planner

## Core Workflow

Every dependency planning follows this pattern:

1. **Parse**: Read vulnerability-object.json from workspace
2. **Identify**: Extract org, repo, and security_alerts
3. **Analyze**: Use github-mcp to inspect target repository files
4. **Plan**: Create update commands for each ecosystem
5. **Flag**: Detect and highlight major version updates

```bash
# Step 1: Read vulnerability data (LOCAL file)
Read vulnerability-object.json

# Step 2: Inspect target repo files (REMOTE via github-mcp)
mcp__github__get_file_contents {org}/{repo}/pyproject.toml
mcp__github__get_file_contents {org}/{repo}/uv.lock

# Step 3: Determine ecosystem and create plan
# Output structured plan with commands
```

## Vulnerability Object Structure

```json
{
  "org": "AgentPOC-Org",
  "repository": {
    "name": "repo-name",
    "html_url": "https://github.com/...",
    "security_alerts": [
      {
        "ecosystem": "pip|npm|go|cargo",
        "package": "package-name",
        "manifests": [{"path": "pyproject.toml", "scope": "runtime"}],
        "current_version": "1.2.3" | null,
        "target_version": "2.0.0",
        "fix_versions": ["1.6.38", "2.0.0"],
        "severity": "critical|high|medium|low",
        "highest_cvss": 7.3,
        "ghsas": ["GHSA-..."],
        "cves": ["CVE-..."]
      }
    ]
  }
}
```

## Major Version Detection

**CRITICAL**: Detect and flag major version updates:

| Current | Target | Type |
|---------|--------|------|
| 1.x.x   | 2.x.x  | MAJOR |
| 0.x.x   | 1.x.x  | MAJOR |
| 1.2.x   | 1.3.x  | MINOR |
| 1.2.3   | 1.2.4  | PATCH |

When major version detected:
- Flag as `[MAJOR_VERSION_UPDATE]`
- Check if minor fix_version available
- Recommend changelog review
- Document potential breaking changes

## Ecosystem File Requirements

| Ecosystem | Manifest | Lock File |
|-----------|----------|-----------|
| pip (uv) | pyproject.toml | uv.lock |
| pip (poetry) | pyproject.toml | poetry.lock |
| npm | package.json | package-lock.json |
| yarn | package.json | yarn.lock |
| pnpm | package.json | pnpm-lock.yaml |
| cargo | Cargo.toml | Cargo.lock |
| go | go.mod | go.sum |

## Update Commands by Ecosystem

### Python (uv)
```bash
uv lock --upgrade-package <package>==<version>
```

### Python (poetry)
```bash
poetry update <package>@<version> --lock
```

### Node.js (npm)
```bash
npm install <package>@<version> --package-lock-only
```

### Node.js (yarn)
```bash
yarn add <package>@<version> --mode update-lockfile
```

### Rust (cargo)
```bash
cargo update -p <package>@<version>
```

### Go
```bash
go get <package>@v<version>
go mod tidy
```

## Output Plan Format

**You MUST follow the template exactly:** [templates/remediation-plan-template.md](templates/remediation-plan-template.md)

**CRITICAL**: You MUST produce the COMPLETE plan with ALL 7 sections fully filled in.
Do NOT produce a summary or abbreviated version. Every section (1-7) must be present
and contain all required fields. Read the template file FIRST, then output your plan
matching its structure exactly.

The plan is saved to `remediation-plan.md` in the workspace directory. The executor agent
reads this file as its primary input, so the structure must be consistent and complete.

Key sections the executor parses:
1. **Section 2 (Package Updates)** -- version info for commit message and major version flags
2. **Section 3 (Files to Checkout)** -- exact file paths for sparse checkout
3. **Section 4 (Update Commands)** -- exact bash commands to run via Bash, in order (NOT manual file edits)
4. **Section 5 (Commit and Push Instructions)** -- branch name, commit message, git push command
5. **Section 7 (Summary)** -- quick reference table

## Deep-Dive Documentation

| Reference | When to Use |
|-----------|-------------|
| [references/ecosystem-detection.md](references/ecosystem-detection.md) | Identifying package managers |
| [references/major-version-handling.md](references/major-version-handling.md) | Breaking change assessment |

## Templates

| Template | Description |
|----------|-------------|
| [templates/remediation-plan-template.md](templates/remediation-plan-template.md) | **Required** output format for the plan (shared with executor) |

## Ready-to-Use Scripts

| Script | Description |
|--------|-------------|
| [scripts/analyze-vulnerabilities.sh](scripts/analyze-vulnerabilities.sh) | Parse and analyze vulnerability JSON |
| [scripts/detect-ecosystem.sh](scripts/detect-ecosystem.sh) | Identify package manager from files |
| [scripts/compare-versions.sh](scripts/compare-versions.sh) | Compare semver versions |

## Plan Sections (all 7 required)

1. **Repository Analysis** — metadata table (org, repo, ecosystems, files)
2. **Package Updates** — one subsection per package with version table + notes
3. **Files to Checkout** — exact file paths in a code block
4. **Update Commands** — exact bash commands in a code block
5. **Commit and Push Instructions** — branch name, commit message, git push command
6. **Verification Checklist** — items the verifier checks after execution
7. **Summary** — table + key decisions

## Anti-Patterns

:x: **WRONG - Producing a summary instead of the full plan:**
```
The plan is to update containerd to v1.7.29 and crypto to v0.45.0...
```

:white_check_mark: **RIGHT - Producing the complete 7-section plan following the template exactly**

❌ **WRONG - Reading local files:**
```bash
cat poetry.lock           # Local file, not target repo
grep "virtualenv" uv.lock # Local file
```

✅ **RIGHT - Using github-mcp:**
```bash
mcp__github__get_file_contents AgentPOC-Org/repo/uv.lock
mcp__github__get_file_contents AgentPOC-Org/repo/pyproject.toml
```
