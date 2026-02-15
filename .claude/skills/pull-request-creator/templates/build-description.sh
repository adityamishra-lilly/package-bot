#!/bin/bash
# Template: Build PR Description
# Purpose: Generate PR body from vulnerability data
# Usage: ./build-description.sh <vulnerability-object.json>
#
# Outputs markdown PR body to stdout

set -euo pipefail

VULN_FILE="${1:?Usage: $0 <vulnerability-object.json>}"

if [[ ! -f "$VULN_FILE" ]]; then
    echo "Error: File not found: $VULN_FILE" >&2
    exit 1
fi

# Extract data from vulnerability object
ORG=$(jq -r '.org' "$VULN_FILE")
REPO=$(jq -r '.repository.name' "$VULN_FILE")

# Build vulnerability table
VULN_TABLE=""
while IFS= read -r line; do
    pkg=$(echo "$line" | jq -r '.package')
    target=$(echo "$line" | jq -r '.target_version')
    severity=$(echo "$line" | jq -r '.severity')
    cves=$(echo "$line" | jq -r '.cves | join(", ")')

    VULN_TABLE+="| $pkg | → $target | $cves | $severity |
"
done < <(jq -c '.repository.security_alerts[]' "$VULN_FILE")

# Check for major version updates
MAJOR_UPDATES=""
while IFS= read -r line; do
    pkg=$(echo "$line" | jq -r '.package')
    current=$(echo "$line" | jq -r '.current_version // "unknown"')
    target=$(echo "$line" | jq -r '.target_version')

    # Simple major version check (first digit)
    if [[ "$current" != "null" ]] && [[ "$current" != "unknown" ]]; then
        current_major="${current%%.*}"
        target_major="${target%%.*}"
        if [[ "$target_major" -gt "$current_major" ]]; then
            MAJOR_UPDATES+="- **$pkg**: $current → $target
"
        fi
    fi
done < <(jq -c '.repository.security_alerts[]' "$VULN_FILE")

# Get manifest files
MANIFEST_FILES=$(jq -r '.repository.security_alerts[].manifests[].path' "$VULN_FILE" | sort -u | sed 's/^/- /')

# Get all GHSAs
GHSAS=$(jq -r '.repository.security_alerts[].ghsas[]' "$VULN_FILE" 2>/dev/null | sort -u | tr '\n' ' ')

# Output PR body (with actual newlines)
cat << EOF
## Security Remediation

This PR updates vulnerable dependencies identified by Dependabot alerts for **$ORG/$REPO**.

### Vulnerabilities Fixed

| Package | Version | CVE | Severity |
|---------|---------|-----|----------|
$VULN_TABLE

### Changes Made

- Updated lock files only (no application code changes)
- No full installs performed
- Minimal file modifications

EOF

if [[ -n "$MAJOR_UPDATES" ]]; then
    cat << EOF
### ⚠️ Major Version Updates

The following packages have major version bumps - review for breaking changes:

$MAJOR_UPDATES
EOF
fi

cat << EOF

### Files Modified

$MANIFEST_FILES

### References

Resolves: $GHSAS

---

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
