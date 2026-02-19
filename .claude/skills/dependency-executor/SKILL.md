---
name: dependency-executor
description: Executes sparse checkout and dependency updates for security remediation. Use when you need to clone minimal files, run ecosystem-specific update commands, and commit changes.
allowed-tools: Read, Bash, Write, MultiEdit, Glob, Grep, TodoWrite
---

# Dependency Update Executor

## Step 0: Read the Remediation Plan (REQUIRED FIRST STEP)

Before doing anything else, read `remediation-plan.md` from the current working directory.
This file was produced by the planner agent and contains the structured plan you must follow.

```
Read remediation-plan.md
```

The plan follows the template at `.claude/skills/dependency-planner/templates/remediation-plan-template.md`.
Extract these sections:

| Plan Section | What You Need |
|-------------|---------------|
| **Section 3: Files to Checkout** | Exact file paths for sparse checkout |
| **Section 4: Update Commands** | Exact bash commands to run, in order |
| **Section 2: Package Updates** | Version info + MAJOR_VERSION_UPDATE flags for commit message |
| **Section 1: Repository Analysis** | Org, repo name, and repository URL |

## Core Workflow

After reading the plan, follow this execution pattern:

1. **Read Plan**: Parse `remediation-plan.md` (Section 3 for files, Section 4 for commands)
2. **Setup**: Create workspace subdirectory
3. **Clone**: Sparse checkout only files listed in Section 3
4. **Branch**: Create fix branch for changes
5. **Update**: Run exact commands from Section 4 in order
6. **Commit**: Commit changes with version info from Section 2

```bash
# Step 1: Read the plan
Read remediation-plan.md

# Step 2: Create workspace
mkdir -p clone && cd clone

# Step 3: Sparse checkout (files from Section 3)
./scripts/sparse-checkout.sh https://github.com/org/repo pyproject.toml uv.lock

# Step 4: Create branch
git checkout -b fix/security-alerts-$(date +%Y%m%d-%H%M%S)

# Step 5: Run update commands (from Section 4)
./scripts/update-pip.sh virtualenv 20.28.1

# Step 6: Commit (version info from Section 2)
git add pyproject.toml uv.lock
git commit -m "chore(deps): fix security vulnerabilities"
```

## Sparse Checkout (Critical)

**Always use sparse checkout to minimize cloned files:**

```bash
# Clone with NO files initially
git clone --no-checkout --filter=blob:none {repo_url} repo
cd repo

# Create fix branch
git checkout -b fix/security-alerts-$(date +%Y%m%d-%H%M%S)

# Configure sparse checkout (use forward slashes on ALL platforms)
git sparse-checkout init --no-cone
git sparse-checkout set pyproject.toml uv.lock

# Checkout only specified files
git checkout
```

## Ecosystem-Specific Update Commands

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

### Node.js (pnpm)
```bash
pnpm update <package>@<version> --lockfile-only
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

## Commit Message Format

```
chore(deps): fix security vulnerabilities

Updates:
- virtualenv: 20.0.0 -> 20.28.1 (CVE-2025-68146)
- filelock: 3.18.0 -> 3.20.3 (CVE-2025-12345)

[MAJOR VERSION UPDATE] containerd: 1.6.0 -> 2.2.0 - review for breaking changes

Resolves: GHSA-xxxx-yyyy, GHSA-aaaa-bbbb
```

## Ready-to-Use Scripts

| Script | Description |
|--------|-------------|
| [scripts/sparse-checkout.sh](scripts/sparse-checkout.sh) | Minimal file checkout |
| [scripts/update-pip.sh](scripts/update-pip.sh) | Update Python (uv/poetry) |
| [scripts/update-npm.sh](scripts/update-npm.sh) | Update Node.js packages |
| [scripts/update-cargo.sh](scripts/update-cargo.sh) | Update Rust packages |
| [scripts/update-go.sh](scripts/update-go.sh) | Update Go modules |
| [scripts/commit-changes.sh](scripts/commit-changes.sh) | Create standardized commit |

## Usage Examples

### Update Python Package (uv)
```bash
./scripts/sparse-checkout.sh https://github.com/org/repo pyproject.toml uv.lock
cd repo
./scripts/update-pip.sh virtualenv 20.28.1 uv
./scripts/commit-changes.sh "virtualenv:20.0.0:20.28.1:CVE-2025-68146"
```

### Update Go Module
```bash
./scripts/sparse-checkout.sh https://github.com/org/repo go.mod go.sum
cd repo
./scripts/update-go.sh golang.org/x/crypto 0.45.0
./scripts/commit-changes.sh "golang.org/x/crypto:0.44.0:0.45.0:CVE-2025-47914"
```

### Update with Major Version Warning
```bash
./scripts/update-go.sh github.com/containerd/containerd 2.2.0
./scripts/commit-changes.sh "containerd:1.6.0:2.2.0:CVE-2024-25621:MAJOR"
```

## Important Rules

1. **Workspace Isolation**: Create clone in subdirectory, not current directory
2. **Minimal Files**: Only checkout files needed for update
3. **No Full Install**: Use lock-only commands to avoid downloading packages
4. **No PR Creation**: Commit only - PR handled by separate agent
5. **Major Version Flag**: Include [MAJOR VERSION UPDATE] in commit if applicable

## Output Format

Report results after execution:

```markdown
## Execution Report

### Workspace
- Path: clone/repo
- Branch: fix/security-alerts-20260215-143022

### Files Checked Out
- pyproject.toml
- uv.lock

### Commands Executed
| Command | Status | Output |
|---------|--------|--------|
| uv lock --upgrade-package virtualenv==20.28.1 | SUCCESS | Updated 1 package |

### Files Modified
- uv.lock (12 lines changed)

### Commit
- Hash: abc1234
- Message: chore(deps): fix security vulnerabilities

### Major Version Updates
- containerd: 1.6.0 -> 2.2.0 [FLAGGED]
```

## References

| Reference | When to Use |
|-----------|-------------|
| [references/sparse-checkout.md](references/sparse-checkout.md) | Git sparse checkout details |
| [references/update-commands.md](references/update-commands.md) | All ecosystem update commands |
