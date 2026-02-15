# Ecosystem Detection Reference

## Overview

This reference documents how to identify the package manager ecosystem from repository files.

## Detection Priority

When multiple package managers could apply, use this priority:

### Python
1. Check for `uv.lock` → **uv**
2. Check for `poetry.lock` → **poetry**
3. Check for `[tool.uv]` in pyproject.toml → **uv**
4. Check for `[tool.poetry]` in pyproject.toml → **poetry**
5. Check for `requirements.txt` → **pip**

### JavaScript/Node.js
1. Check for `pnpm-lock.yaml` → **pnpm**
2. Check for `yarn.lock` → **yarn**
3. Check for `package-lock.json` → **npm**

### Other Languages
- `Cargo.toml` + `Cargo.lock` → **cargo** (Rust)
- `go.mod` + `go.sum` → **go** (Go)
- `Gemfile` + `Gemfile.lock` → **bundler** (Ruby)
- `composer.json` + `composer.lock` → **composer** (PHP)

## File Requirements by Ecosystem

| Ecosystem | Required for Update | Lock File |
|-----------|---------------------|-----------|
| uv | pyproject.toml | uv.lock |
| poetry | pyproject.toml | poetry.lock |
| pip | requirements.txt | - |
| npm | package.json | package-lock.json |
| yarn | package.json | yarn.lock |
| pnpm | package.json | pnpm-lock.yaml |
| cargo | Cargo.toml | Cargo.lock |
| go | go.mod | go.sum |

## Ecosystem from Manifest Path

The vulnerability object contains `manifests[].path` which indicates the ecosystem:

```json
{
  "manifests": [
    {"path": "go.mod", "scope": "runtime"}
  ]
}
```

| Manifest Path | Ecosystem |
|--------------|-----------|
| go.mod | go |
| pyproject.toml | pip (uv/poetry) |
| requirements.txt | pip |
| package.json | npm/yarn/pnpm |
| Cargo.toml | cargo |
| Gemfile | bundler |

## Detecting Lock File Type

```bash
# For Python projects with pyproject.toml
if [ -f "uv.lock" ]; then
    ECOSYSTEM="uv"
elif [ -f "poetry.lock" ]; then
    ECOSYSTEM="poetry"
elif grep -q "\[tool.uv\]" pyproject.toml; then
    ECOSYSTEM="uv"
elif grep -q "\[tool.poetry\]" pyproject.toml; then
    ECOSYSTEM="poetry"
fi
```

## GitHub MCP Detection

When using github-mcp to detect ecosystem:

```bash
# List files in repository root
mcp__github__list_files {org}/{repo}

# Check for specific lock files
mcp__github__get_file_contents {org}/{repo}/uv.lock
mcp__github__get_file_contents {org}/{repo}/poetry.lock
```
