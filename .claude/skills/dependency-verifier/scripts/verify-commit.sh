#!/bin/bash
# Script: Verify Commit
# Purpose: Check that commit contains correct changes for security update
# Usage: ./verify-commit.sh [expected-files...]
#
# Verifies:
# - Branch name follows convention
# - Commit message contains CVE/GHSA references
# - Only expected files are modified

set -euo pipefail

EXPECTED_FILES=("$@")

echo "=== Commit Verification ==="
echo ""

ISSUES=()

# Check branch name
BRANCH=$(git branch --show-current 2>/dev/null || echo "DETACHED")
echo "Branch: $BRANCH"

if [[ "$BRANCH" =~ ^fix/security-alerts-[0-9]{8}-[0-9]{6}$ ]]; then
    echo "✓ Branch name follows convention"
else
    echo "⚠ Branch name doesn't match expected pattern (fix/security-alerts-YYYYMMDD-HHMMSS)"
    ISSUES+=("Branch name convention")
fi

echo ""

# Check last commit message
COMMIT_MSG=$(git log -1 --pretty=%B 2>/dev/null || echo "")
COMMIT_HASH=$(git log -1 --pretty=%h 2>/dev/null || echo "NONE")

echo "Last commit: $COMMIT_HASH"
echo ""

# Check for security keywords in commit message
if echo "$COMMIT_MSG" | grep -qiE "(CVE-|GHSA-|security|vulnerability|deps)"; then
    echo "✓ Commit message contains security references"
else
    echo "⚠ Commit message missing security references"
    ISSUES+=("Missing CVE/GHSA references")
fi

# Check for major version warning if applicable
if echo "$COMMIT_MSG" | grep -qi "MAJOR"; then
    echo "✓ Major version update documented"
fi

echo ""

# Check modified files
echo "Modified files in last commit:"
MODIFIED_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null || echo "")

if [[ -z "$MODIFIED_FILES" ]]; then
    echo "⚠ No files in commit"
    ISSUES+=("Empty commit")
else
    echo "$MODIFIED_FILES"
    echo ""

    # Check if only expected files modified
    if [[ ${#EXPECTED_FILES[@]} -gt 0 ]]; then
        echo "Checking expected files..."
        for file in $MODIFIED_FILES; do
            FOUND=0
            for expected in "${EXPECTED_FILES[@]}"; do
                if [[ "$file" == "$expected" ]]; then
                    FOUND=1
                    break
                fi
            done
            if [[ $FOUND -eq 0 ]]; then
                echo "⚠ Unexpected file: $file"
                ISSUES+=("Unexpected file: $file")
            fi
        done
    fi

    # Check for sensitive files
    for file in $MODIFIED_FILES; do
        if [[ "$file" =~ \.(env|secret|key|pem|p12)$ ]] || [[ "$file" == ".env" ]]; then
            echo "✗ Sensitive file modified: $file"
            ISSUES+=("Sensitive file: $file")
        fi
    done
fi

echo ""

# Check for uncommitted changes
UNCOMMITTED=$(git status --porcelain 2>/dev/null || echo "")
if [[ -n "$UNCOMMITTED" ]]; then
    echo "⚠ Uncommitted changes detected:"
    echo "$UNCOMMITTED"
    ISSUES+=("Uncommitted changes")
else
    echo "✓ No uncommitted changes"
fi

echo ""
echo "=== Summary ==="

if [[ ${#ISSUES[@]} -eq 0 ]]; then
    echo "✓ All commit checks passed"
    exit 0
else
    echo "Issues found:"
    for issue in "${ISSUES[@]}"; do
        echo "  - $issue"
    done
    exit 1
fi
