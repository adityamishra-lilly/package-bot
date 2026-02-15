---
name: dependency-verifier
description: Verifies that dependency updates were successful. Use when you need to validate package versions, check file integrity, and confirm readiness for PR creation.
allowed-tools: Read, Bash, Grep, Glob, TodoWrite
---

# Dependency Update Verifier

## Core Workflow

Every verification follows this pattern:

1. **Version Check**: Verify packages at expected versions
2. **File Integrity**: Validate lock files are properly formatted
3. **Commit Check**: Ensure commit contains correct changes
4. **Major Version**: Confirm major updates are documented
5. **Ready Check**: Determine if PR-ready

```bash
# Step 1: Check package versions
./scripts/verify-versions.sh uv.lock virtualenv 20.28.1

# Step 2: Validate file format
./scripts/validate-lockfile.sh uv.lock

# Step 3: Check commit
./scripts/verify-commit.sh

# Step 4: Generate report
./scripts/generate-report.sh
```

## Verification Checklist

### 1. Version Verification
- [ ] All target packages updated to expected versions
- [ ] No unintended version changes to other packages
- [ ] Fix versions satisfy vulnerability requirements

### 2. File Integrity
- [ ] Lock file parses correctly (valid TOML/JSON/YAML)
- [ ] Only expected files modified
- [ ] No extra files included in commit

### 3. Commit Verification
- [ ] Commit message follows conventions
- [ ] Branch named correctly (fix/security-alerts-*)
- [ ] All changes are security-related

### 4. Major Version Verification
- [ ] Major updates flagged in commit message
- [ ] Alternative minor versions noted if available
- [ ] Breaking change warnings included

## Ecosystem-Specific Verification

### Python (uv)

```bash
# Check package version in uv.lock
grep -A5 'name = "virtualenv"' uv.lock | grep 'version = "20.28.1"'

# Validate TOML format
python -c "import tomllib; tomllib.load(open('uv.lock', 'rb'))"
```

### Python (poetry)

```bash
# Check package version in poetry.lock
grep -A3 'name = "virtualenv"' poetry.lock | grep 'version = "20.28.1"'

# Validate TOML format
python -c "import tomllib; tomllib.load(open('poetry.lock', 'rb'))"
```

### Node.js (npm)

```bash
# Check package version in package-lock.json
jq '.packages["node_modules/lodash"].version' package-lock.json

# Validate JSON format
jq . package-lock.json > /dev/null
```

### Rust (cargo)

```bash
# Check package version in Cargo.lock
grep -A2 'name = "serde"' Cargo.lock | grep 'version = "1.0.0"'

# Validate TOML format
cargo metadata --format-version 1 > /dev/null
```

### Go

```bash
# Check module version in go.mod
grep 'golang.org/x/crypto v0.45.0' go.mod

# Verify go.sum has entry
grep 'golang.org/x/crypto v0.45.0' go.sum
```

## Ready-to-Use Scripts

| Script | Description |
|--------|-------------|
| [scripts/verify-versions.sh](scripts/verify-versions.sh) | Check package versions |
| [scripts/validate-lockfile.sh](scripts/validate-lockfile.sh) | Validate lock file format |
| [scripts/verify-commit.sh](scripts/verify-commit.sh) | Check commit contents |
| [scripts/generate-report.sh](scripts/generate-report.sh) | Generate verification report |

## Output Report Format

```markdown
## Verification Report

### Status: SUCCESS | FAILURE | PARTIAL

### Packages Verified
| Package | Expected | Actual | Status |
|---------|----------|--------|--------|
| virtualenv | 20.28.1 | 20.28.1 | ✓ OK |
| filelock | 3.20.3 | 3.20.3 | ✓ OK |

### Major Version Updates
| Package | From | To | Status |
|---------|------|-----|--------|
| containerd | 1.6.0 | 2.2.0 | ⚠ MAJOR - Documented |

### Files Checked
| File | Format | Status |
|------|--------|--------|
| uv.lock | TOML | ✓ Valid |
| pyproject.toml | TOML | ✓ Valid |

### Commit Check
- Branch: fix/security-alerts-20260215-143022 ✓
- Message: Contains CVE references ✓
- Files: Only lock files modified ✓

### Issues Found
- None

### Ready for PR: YES
```

## Failure Scenarios

### Version Mismatch
```markdown
### Status: FAILURE

### Issues Found
- virtualenv expected 20.28.1 but found 20.27.0

### Remediation
1. Re-run executor with correct version
2. Check if version is available in registry
```

### Invalid Lock File
```markdown
### Status: FAILURE

### Issues Found
- uv.lock: Invalid TOML at line 423

### Remediation
1. Delete uv.lock and regenerate
2. Check for merge conflicts
```

### Uncommitted Changes
```markdown
### Status: FAILURE

### Issues Found
- Uncommitted changes in workspace

### Remediation
1. Review changes with 'git diff'
2. Stage and commit with proper message
```

## References

| Reference | When to Use |
|-----------|-------------|
| [references/version-parsing.md](references/version-parsing.md) | Parsing versions from lock files |
| [references/lockfile-formats.md](references/lockfile-formats.md) | Lock file format specifications |
