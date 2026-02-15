#!/bin/bash
# Script: Commit Changes
# Purpose: Create standardized commit for security updates
# Usage: ./commit-changes.sh "pkg1:old:new:CVE" ["pkg2:old:new:CVE:MAJOR"] ...
#
# Each argument format: package:old_version:new_version:CVE[:MAJOR]
# Add :MAJOR suffix for major version updates

set -euo pipefail

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 \"package:old_version:new_version:CVE\" ..."
    echo "Example: $0 \"virtualenv:20.0.0:20.28.1:CVE-2025-68146\""
    echo "For major: $0 \"containerd:1.6.0:2.2.0:CVE-2024-25621:MAJOR\""
    exit 1
fi

UPDATES=()
MAJOR_UPDATES=()
GHSAS=()
CVES=()

# Parse arguments
for arg in "$@"; do
    IFS=':' read -r pkg old new cve major <<< "$arg"

    if [[ "$major" == "MAJOR" ]]; then
        MAJOR_UPDATES+=("$pkg: $old -> $new")
        UPDATES+=("$pkg: $old -> $new ($cve) [MAJOR]")
    else
        UPDATES+=("$pkg: $old -> $new ($cve)")
    fi

    if [[ "$cve" == CVE-* ]]; then
        CVES+=("$cve")
    elif [[ "$cve" == GHSA-* ]]; then
        GHSAS+=("$cve")
    fi
done

# Build commit message
COMMIT_MSG="chore(deps): fix security vulnerabilities

Updates:"

for update in "${UPDATES[@]}"; do
    COMMIT_MSG+=$'\n'"- $update"
done

# Add major version warning if any
if [[ ${#MAJOR_UPDATES[@]} -gt 0 ]]; then
    COMMIT_MSG+=$'\n'$'\n'"[MAJOR VERSION UPDATE] The following packages have major version bumps - review for breaking changes:"
    for major in "${MAJOR_UPDATES[@]}"; do
        COMMIT_MSG+=$'\n'"- $major"
    done
fi

# Add resolves line
if [[ ${#GHSAS[@]} -gt 0 ]] || [[ ${#CVES[@]} -gt 0 ]]; then
    COMMIT_MSG+=$'\n'$'\n'"Resolves:"
    for ghsa in "${GHSAS[@]}"; do
        COMMIT_MSG+=" $ghsa"
    done
    for cve in "${CVES[@]}"; do
        COMMIT_MSG+=" $cve"
    done
fi

echo "=== Commit Message ==="
echo "$COMMIT_MSG"
echo ""

# Stage all changes
echo "Staging changes..."
git add -A

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "No changes to commit"
    exit 0
fi

# Show what will be committed
echo ""
echo "=== Files to Commit ==="
git diff --cached --name-only

# Create commit
echo ""
echo "Creating commit..."
git commit -m "$COMMIT_MSG"

# Show commit info
echo ""
echo "=== Commit Created ==="
git log -1 --oneline
