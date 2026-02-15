---
name: dependency-executor
description: Executes sparse checkout and dependency updates for security remediation. Use when you need to clone minimal files, run ecosystem-specific update commands, and commit changes.
allowed-tools: Read, Bash, Write, MultiEdit, Glob, Grep, TodoWrite
---

# Dependency Update Executor

## Core Workflow

Every dependency update execution follows this pattern:

1. **Setup**: Create workspace subdirectory
2. **Clone**: Sparse checkout only required files
3. **Branch**: Create fix branch for changes
4. **Update**: Run ecosystem-specific update commands
5. **Commit**: Commit changes with descriptive message

```bash
# Step 1: Create workspace
mkdir -p clone && cd clone

# Step 2: Sparse checkout
./scripts/sparse-checkout.sh https://github.com/org/repo pyproject.toml uv.lock

# Step 3: Create branch
git checkout -b fix/security-alerts-$(date +%Y%m%d-%H%M%S)

# Step 4: Update packages
./scripts/update-pip.sh virtualenv 20.28.1

# Step 5: Commit
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
