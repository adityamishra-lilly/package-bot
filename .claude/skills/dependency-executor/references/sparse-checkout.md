# Sparse Checkout Reference

## Overview

Sparse checkout allows cloning a repository with only specific files, reducing network transfer and disk usage.

## Basic Commands

```bash
# Clone with no files and blob filter (minimal transfer)
git clone --no-checkout --filter=blob:none <repo-url> <directory>

# Initialize sparse checkout
git sparse-checkout init --no-cone

# Set files to checkout
git sparse-checkout set file1.txt path/to/file2.json

# Perform checkout
git checkout
```

## Windows Compatibility

**Always use forward slashes (`/`) in file paths, even on Windows:**

```bash
# CORRECT (works on all platforms)
git sparse-checkout set pyproject.toml src/main.py

# WRONG (fails on Windows)
git sparse-checkout set pyproject.toml src\main.py
```

## Cone vs No-Cone Mode

### No-Cone Mode (Recommended)
- Supports individual file paths
- Works with any file pattern
- Better cross-platform compatibility

```bash
git sparse-checkout init --no-cone
git sparse-checkout set pyproject.toml uv.lock
```

### Cone Mode
- Directory-based
- More efficient for large directories
- May not work with individual files

```bash
git sparse-checkout init --cone
git sparse-checkout set src/ lib/
```

## Common Patterns

### Single File
```bash
git sparse-checkout set README.md
```

### Multiple Files
```bash
git sparse-checkout set pyproject.toml uv.lock poetry.lock
```

### Directory
```bash
git sparse-checkout set src/
```

### Mixed
```bash
git sparse-checkout set pyproject.toml src/main.py tests/
```

## Verification

```bash
# List files in sparse checkout
git sparse-checkout list

# Show status
git status

# List checked out files
ls -la
```

## Troubleshooting

### Files Not Appearing
1. Check file exists in repository
2. Verify path is correct (case-sensitive)
3. Run `git checkout` after setting sparse-checkout

### "error: Sparse checkout leaves no entry"
- File path doesn't exist in repository
- Check spelling and case

### Windows Line Endings
- Use `git config core.autocrlf input` to avoid issues

## Full Workflow Example

```bash
# Create workspace
mkdir -p workspace && cd workspace

# Clone minimal
git clone --no-checkout --filter=blob:none https://github.com/org/repo repo
cd repo

# Create branch
git checkout -b fix/security-updates

# Setup sparse checkout
git sparse-checkout init --no-cone
git sparse-checkout set pyproject.toml uv.lock

# Checkout files
git checkout

# Verify
ls -la
# Should show only: pyproject.toml, uv.lock, .git/
```
