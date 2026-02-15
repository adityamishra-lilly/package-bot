#!/bin/bash
# Script: Check PR Diff
# Purpose: Validate PR diff contains only expected changes
# Usage: ./check-diff.sh <diff_file|->

set -euo pipefail

DIFF_INPUT="${1:--}"

echo "=== Checking PR Diff ==="

# Read diff from file or stdin
if [[ "$DIFF_INPUT" == "-" ]]; then
    DIFF_CONTENT=$(cat)
else
    DIFF_CONTENT=$(cat "$DIFF_INPUT")
fi

# Extract modified files
FILES_CHANGED=$(echo "$DIFF_CONTENT" | grep -E "^diff --git" | sed 's/diff --git a\///' | sed 's/ b\/.*//' || true)

echo "Files changed:"
echo "$FILES_CHANGED"
echo ""

# Check for lock files
LOCK_FILES=$(echo "$FILES_CHANGED" | grep -E "\.(lock|sum)$|package-lock\.json|pnpm-lock\.yaml" || true)
echo "Lock files: ${LOCK_FILES:-none}"

# Check for manifest files
MANIFEST_FILES=$(echo "$FILES_CHANGED" | grep -E "pyproject\.toml|package\.json|Cargo\.toml|go\.mod" || true)
echo "Manifest files: ${MANIFEST_FILES:-none}"

# Check for sensitive files (should be empty)
SENSITIVE_FILES=$(echo "$FILES_CHANGED" | grep -E "\.env|\.secret|\.key|\.pem|credentials|\.npmrc" || true)
echo "Sensitive files: ${SENSITIVE_FILES:-none}"

# Check for source code files (should be empty for security updates)
SOURCE_FILES=$(echo "$FILES_CHANGED" | grep -E "\.(py|js|ts|rs|go)$" | grep -v "\.d\.ts$" || true)
echo "Source files: ${SOURCE_FILES:-none}"

echo ""
echo "=== Validation Results ==="

VALID=true

if [[ -z "$LOCK_FILES" ]]; then
    echo "[WARNING] No lock files modified"
fi

if [[ -n "$SENSITIVE_FILES" ]]; then
    echo "[ERROR] Sensitive files detected in diff!"
    VALID=false
fi

if [[ -n "$SOURCE_FILES" ]]; then
    echo "[WARNING] Source code files modified - verify these are expected"
fi

if [[ "$VALID" == "true" ]]; then
    echo ""
    echo "Diff validation: PASSED"
    exit 0
else
    echo ""
    echo "Diff validation: FAILED"
    exit 1
fi
