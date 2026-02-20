---
name: dependency-executor
description: Executes sparse checkout and dependency updates for security remediation. Use when you need to clone minimal files, run ecosystem-specific update commands, and commit/push changes.
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
| **Section 1: Repository Analysis** | Org, repo name, and repository URL |
| **Section 2: Package Updates** | Version info + MAJOR_VERSION_UPDATE flags for commit message |
| **Section 3: Files to Checkout** | Exact file paths for sparse checkout |
| **Section 4: Update Commands** | Exact bash commands to run, in order |
| **Section 5: Commit and Push Instructions** | Branch name, commit message, push command |

## Core Workflow

After reading the plan, follow this execution pattern:

1. **Read Plan**: Parse `remediation-plan.md` (all sections)
2. **Setup**: Create workspace subdirectory
3. **Clone**: Sparse checkout only files listed in Section 3
4. **Branch**: Create fix branch
5. **Update**: Run exact commands from Section 4 via Bash
6. **Commit**: Stage and commit changes
7. **Push**: Push branch to origin

```bash
# Step 1: Read the plan
Read remediation-plan.md

# Step 2: Create workspace
mkdir -p clone && cd clone

# Step 3: Sparse checkout (files from Section 3)
git clone --no-checkout --filter=blob:none https://github.com/org/repo repo
cd repo

# Step 4: Create fix branch
git checkout -b fix/security-alerts-$(date +%Y%m%d-%H%M%S)

# Step 5: Configure sparse checkout
git sparse-checkout init --no-cone
git sparse-checkout set pyproject.toml uv.lock
git checkout

# Step 6: Run update commands (from Section 4) — MUST use Bash, NOT manual edits
uv lock --upgrade-package virtualenv==20.28.1

# Step 7: Commit and push (from Section 5)
git add -A
git commit -m "chore(deps): fix security vulnerabilities"
git push -u origin fix/security-alerts-YYYYMMDD-HHMMSS
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

**CRITICAL: You MUST run these commands via the Bash tool. Do NOT manually edit
manifest files (go.mod, pyproject.toml, package.json, etc.) or lock files
(go.sum, uv.lock, package-lock.json, etc.). The commands handle all file changes.**

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

## Commit and Push

After running update commands, commit and push the changes:

```bash
# Stage all changes
git add -A

# Commit with structured message
git commit -m "chore(deps): fix security vulnerabilities

Updates:
- virtualenv: 20.0.0 -> 20.28.1 (CVE-2025-68146)

Resolves: GHSA-xxxx-yyyy"

# Push to origin
git push -u origin fix/security-alerts-YYYYMMDD-HHMMSS
```

### Commit Message Format

Build the commit message from Section 2 (Package Updates):

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
# Sparse checkout
git clone --no-checkout --filter=blob:none https://github.com/org/repo repo
cd repo && git checkout -b fix/security-alerts-$(date +%Y%m%d-%H%M%S)
git sparse-checkout init --no-cone
git sparse-checkout set pyproject.toml uv.lock && git checkout

# Run update command — NOT manual file edits
uv lock --upgrade-package virtualenv==20.28.1

# Commit and push
git add -A && git commit -m "chore(deps): fix security vulnerabilities"
git push -u origin fix/security-alerts-YYYYMMDD-HHMMSS
```

### Update Go Module
```bash
# Sparse checkout
git clone --no-checkout --filter=blob:none https://github.com/org/repo repo
cd repo && git checkout -b fix/security-alerts-$(date +%Y%m%d-%H%M%S)
git sparse-checkout init --no-cone
git sparse-checkout set go.mod go.sum && git checkout

# Run update commands — NOT manual file edits
go get golang.org/x/crypto@v0.45.0
go mod tidy

# Commit and push
git add -A && git commit -m "chore(deps): fix security vulnerabilities"
git push -u origin fix/security-alerts-YYYYMMDD-HHMMSS
```

## Important Rules

1. **Workspace Isolation**: Create clone in subdirectory, not current directory
2. **Minimal Files**: Only checkout files needed for update
3. **No Full Install**: Use lock-only commands to avoid downloading packages
4. **Run Commands via Bash**: ALWAYS run update commands via Bash tool. NEVER manually edit manifest or lock files
5. **Git Push**: Use `git push -u origin <branch>` to push changes after committing
6. **No PR Creation**: PR creation is handled by a separate agent
7. **Major Version Flag**: Include [MAJOR VERSION UPDATE] in commit message if applicable

## Anti-Patterns

**NEVER manually edit dependency files:**
```
# WRONG — do not use Write/Edit to modify go.mod, go.sum, pyproject.toml, uv.lock, etc.
Write go.mod with modified content
Edit go.mod replacing version string
```

**ALWAYS run the ecosystem update command:**
```bash
# RIGHT — run the actual command that updates the files correctly
go get github.com/containerd/containerd@v1.7.29
go mod tidy
```

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

### Commit and Push
- Commit: abc1234
- Branch: fix/security-alerts-20260215-143022
- Push: SUCCESS

### Major Version Updates
- containerd: 1.6.0 -> 2.2.0 [FLAGGED]
```

## References

| Reference | When to Use |
|-----------|-------------|
| [references/sparse-checkout.md](references/sparse-checkout.md) | Git sparse checkout details |
| [references/update-commands.md](references/update-commands.md) | All ecosystem update commands |
