#!/bin/bash
# Template: Compare Versions
# Purpose: Compare semantic versions and detect major/minor/patch changes
# Usage: ./compare-versions.sh <current-version> <target-version>
#
# Output:
# - Version change type (MAJOR, MINOR, PATCH)
# - Whether this is a breaking change risk

set -euo pipefail

CURRENT="${1:?Usage: $0 <current-version> <target-version>}"
TARGET="${2:?Usage: $0 <current-version> <target-version>}"

# Parse semver components
parse_semver() {
    local version="$1"
    # Remove 'v' prefix if present
    version="${version#v}"
    # Remove any pre-release suffix for comparison
    version="${version%%-*}"
    version="${version%%+*}"

    local major minor patch
    IFS='.' read -r major minor patch <<< "$version"

    echo "${major:-0} ${minor:-0} ${patch:-0}"
}

# Compare versions
compare_versions() {
    local curr_parts=($1)
    local tgt_parts=($2)

    local curr_major="${curr_parts[0]}"
    local curr_minor="${curr_parts[1]}"
    local curr_patch="${curr_parts[2]}"

    local tgt_major="${tgt_parts[0]}"
    local tgt_minor="${tgt_parts[1]}"
    local tgt_patch="${tgt_parts[2]}"

    if [[ "$tgt_major" -gt "$curr_major" ]]; then
        echo "MAJOR"
    elif [[ "$curr_major" == "0" ]] && [[ "$tgt_major" == "1" ]]; then
        # 0.x -> 1.x is always major
        echo "MAJOR"
    elif [[ "$curr_major" == "0" ]] && [[ "$tgt_minor" -gt "$curr_minor" ]]; then
        # In 0.x.y, minor bumps can be breaking
        echo "MAJOR"
    elif [[ "$tgt_minor" -gt "$curr_minor" ]]; then
        echo "MINOR"
    elif [[ "$tgt_patch" -gt "$curr_patch" ]]; then
        echo "PATCH"
    else
        echo "UNCHANGED"
    fi
}

# Main
CURR_PARTS=$(parse_semver "$CURRENT")
TGT_PARTS=$(parse_semver "$TARGET")

CHANGE_TYPE=$(compare_versions "$CURR_PARTS" "$TGT_PARTS")

echo "Current version: $CURRENT"
echo "Target version: $TARGET"
echo "Change type: $CHANGE_TYPE"

case "$CHANGE_TYPE" in
    "MAJOR")
        echo ""
        echo "⚠️  WARNING: MAJOR VERSION UPDATE"
        echo "   - Breaking changes are likely"
        echo "   - Review changelog before merging"
        echo "   - Consider if minor fix version is available"
        ;;
    "MINOR")
        echo ""
        echo "ℹ️  MINOR VERSION UPDATE"
        echo "   - New features, but should be backward compatible"
        echo "   - Low risk of breaking changes"
        ;;
    "PATCH")
        echo ""
        echo "✅ PATCH VERSION UPDATE"
        echo "   - Bug fixes only"
        echo "   - Safe to update"
        ;;
esac

# Exit with code indicating if breaking change
if [[ "$CHANGE_TYPE" == "MAJOR" ]]; then
    exit 1
else
    exit 0
fi
