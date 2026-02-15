#!/bin/bash
# Script: Review Pull Request
# Purpose: Automated PR review for security updates
# Usage: ./review-pr.sh <owner> <repo> <pr_number>

set -euo pipefail

OWNER="${1:?Usage: $0 <owner> <repo> <pr_number>}"
REPO="${2:?Usage: $0 <owner> <repo> <pr_number>}"
PR_NUMBER="${3:?Usage: $0 <owner> <repo> <pr_number>}"

echo "=== PR Review: $OWNER/$REPO #$PR_NUMBER ==="

# Initialize check results
TITLE_CHECK="PENDING"
CVE_CHECK="PENDING"
LOCK_FILES_ONLY="PENDING"
NO_SENSITIVE_FILES="PENDING"
FORMATTING_CHECK="PENDING"
MAJOR_VERSION_CHECK="PENDING"

# Get PR details (via gh CLI or github-mcp)
echo "Fetching PR details..."

# Check 1: Title format
echo ""
echo "=== Check 1: Title Format ==="
# Title should indicate security update
# Good: "Security: Update vulnerable dependencies"
# Bad: "Update stuff"

# Check 2: CVE references
echo ""
echo "=== Check 2: CVE References ==="
# Body should contain CVE-XXXX-XXXXX or GHSA-XXXX-XXXX-XXXX patterns

# Check 3: Lock files only
echo ""
echo "=== Check 3: Lock Files Only ==="
# Only .lock, .json (package-lock), .sum files should be modified

# Check 4: No sensitive files
echo ""
echo "=== Check 4: No Sensitive Files ==="
# No .env, credentials, secrets, keys in diff

# Check 5: Major version warnings
echo ""
echo "=== Check 5: Major Version Warnings ==="
# Major version updates should be flagged with warning emoji

# Check 6: Formatting
echo ""
echo "=== Check 6: Markdown Formatting ==="
# Tables render correctly, links valid

echo ""
echo "=== Review Summary ==="
echo "Title Check: $TITLE_CHECK"
echo "CVE References: $CVE_CHECK"
echo "Lock Files Only: $LOCK_FILES_ONLY"
echo "No Sensitive Files: $NO_SENSITIVE_FILES"
echo "Major Version Warnings: $MAJOR_VERSION_CHECK"
echo "Formatting: $FORMATTING_CHECK"

# Note: Actual PR review should be done via github-mcp
# This script prepares the checklist for the agent
