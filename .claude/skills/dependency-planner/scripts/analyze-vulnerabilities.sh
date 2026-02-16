#!/bin/bash
# Template: Analyze Vulnerabilities
# Purpose: Parse vulnerability-object.json and extract key information
# Usage: ./analyze-vulnerabilities.sh [vulnerability-file]
#
# This script analyzes the vulnerability object and outputs:
# - Repository information
# - List of vulnerable packages by ecosystem
# - Major version updates detected
# - Recommended update order (by severity)

set -euo pipefail

VULN_FILE="${1:-vulnerability-object.json}"

if [[ ! -f "$VULN_FILE" ]]; then
    echo "Error: Vulnerability file not found: $VULN_FILE"
    exit 1
fi

echo "=== Vulnerability Analysis ==="
echo ""

# Extract repository info
ORG=$(jq -r '.org' "$VULN_FILE")
REPO=$(jq -r '.repository.name' "$VULN_FILE")
REPO_URL=$(jq -r '.repository.html_url' "$VULN_FILE")

echo "Repository: $ORG/$REPO"
echo "URL: $REPO_URL"
echo ""

# Count alerts by severity
echo "=== Severity Summary ==="
jq -r '.repository.security_alerts[] | .severity' "$VULN_FILE" | sort | uniq -c | sort -rn
echo ""

# List packages by ecosystem
echo "=== Packages by Ecosystem ==="
jq -r '.repository.security_alerts[] | "\(.ecosystem): \(.package) (\(.current_version // "unknown") -> \(.target_version))"' "$VULN_FILE"
echo ""

# Detect major version updates
echo "=== Major Version Updates ==="
jq -r '.repository.security_alerts[] |
    select(.current_version != null) |
    select(
        (.current_version | split(".")[0] | tonumber) <
        (.target_version | split(".")[0] | tonumber)
    ) |
    "[MAJOR] \(.package): \(.current_version) -> \(.target_version)"' "$VULN_FILE" 2>/dev/null || echo "None detected (or current_version is null)"
echo ""

# List required manifest files
echo "=== Required Files ==="
jq -r '.repository.security_alerts[].manifests[].path' "$VULN_FILE" | sort -u
echo ""

# Output recommended update order (critical/high first)
echo "=== Recommended Update Order ==="
jq -r '.repository.security_alerts | sort_by(
    if .severity == "critical" then 0
    elif .severity == "high" then 1
    elif .severity == "medium" then 2
    else 3 end
) | .[] | "[\(.severity | ascii_upcase)] \(.package)@\(.target_version)"' "$VULN_FILE"
