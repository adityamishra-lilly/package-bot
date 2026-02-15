#!/bin/bash
# Script: Generate Verification Report
# Purpose: Create comprehensive verification report
# Usage: ./generate-report.sh <lockfile> <package1:version1> [package2:version2] ...
#
# Outputs markdown report to stdout

set -euo pipefail

LOCKFILE="${1:?Usage: $0 <lockfile> <package1:version1> ...}"
shift
PACKAGES=("$@")

# Get script directory for relative imports
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "## Verification Report"
echo ""
echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# Run version verification
echo "### Packages Verified"
echo ""
if "$SCRIPT_DIR/verify-versions.sh" "$LOCKFILE" "${PACKAGES[@]}" 2>&1 | grep -E "^\|"; then
    VERSION_STATUS="SUCCESS"
else
    VERSION_STATUS="FAILURE"
fi

echo ""

# Run lock file validation
echo "### File Validation"
echo ""
echo "| File | Format | Status |"
echo "|------|--------|--------|"

if "$SCRIPT_DIR/validate-lockfile.sh" "$LOCKFILE" > /dev/null 2>&1; then
    BASENAME=$(basename "$LOCKFILE")
    echo "| $BASENAME | $(echo "$LOCKFILE" | grep -oE '\.[^.]+$' | tr -d '.') | ✓ Valid |"
    FILE_STATUS="SUCCESS"
else
    BASENAME=$(basename "$LOCKFILE")
    echo "| $BASENAME | $(echo "$LOCKFILE" | grep -oE '\.[^.]+$' | tr -d '.') | ✗ Invalid |"
    FILE_STATUS="FAILURE"
fi

echo ""

# Run commit verification
echo "### Commit Check"
echo ""
BRANCH=$(git branch --show-current 2>/dev/null || echo "UNKNOWN")
COMMIT=$(git log -1 --pretty=%h 2>/dev/null || echo "NONE")
COMMIT_MSG=$(git log -1 --pretty=%s 2>/dev/null || echo "")

echo "- Branch: \`$BRANCH\`"
echo "- Commit: \`$COMMIT\`"
echo "- Message: $COMMIT_MSG"

if [[ "$BRANCH" =~ ^fix/security-alerts ]]; then
    echo "- Branch naming: ✓"
    COMMIT_STATUS="SUCCESS"
else
    echo "- Branch naming: ⚠ Non-standard"
    COMMIT_STATUS="WARNING"
fi

echo ""

# Check for major version updates
echo "### Major Version Updates"
echo ""
MAJOR_FOUND=0
for pkg_ver in "${PACKAGES[@]}"; do
    IFS=':' read -r package version <<< "$pkg_ver"
    # This is a placeholder - actual major version detection would need current version
    echo "- $package@$version: Checking..."
done
echo ""

# Determine overall status
echo "### Status"
echo ""

if [[ "$VERSION_STATUS" == "SUCCESS" ]] && [[ "$FILE_STATUS" == "SUCCESS" ]]; then
    echo "**Status: SUCCESS** ✓"
    echo ""
    echo "### Ready for PR: YES"
    EXIT_CODE=0
elif [[ "$VERSION_STATUS" == "FAILURE" ]]; then
    echo "**Status: FAILURE** ✗"
    echo ""
    echo "### Ready for PR: NO"
    echo ""
    echo "**Reason:** Package versions do not match expected values"
    EXIT_CODE=1
else
    echo "**Status: PARTIAL** ⚠"
    echo ""
    echo "### Ready for PR: REVIEW NEEDED"
    EXIT_CODE=2
fi

exit $EXIT_CODE
