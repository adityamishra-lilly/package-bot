#!/bin/bash
# Script: Verify Versions
# Purpose: Check that packages are at expected versions in lock files
# Usage: ./verify-versions.sh <lockfile> <package1:version1> [package2:version2] ...
#
# Returns exit code 0 if all versions match, 1 otherwise

set -euo pipefail

LOCKFILE="${1:?Usage: $0 <lockfile> <package1:version1> ...}"
shift
PACKAGES=("$@")

if [[ ${#PACKAGES[@]} -eq 0 ]]; then
    echo "Error: At least one package:version pair required"
    exit 1
fi

echo "=== Version Verification ==="
echo "Lock file: $LOCKFILE"
echo ""

# Detect lock file type
detect_type() {
    case "$1" in
        *.lock)
            if head -1 "$1" | grep -q "^\[\["; then
                echo "uv"
            elif head -1 "$1" | grep -q "^\[metadata\]"; then
                echo "poetry"
            else
                echo "cargo"
            fi
            ;;
        *package-lock.json)
            echo "npm"
            ;;
        *yarn.lock)
            echo "yarn"
            ;;
        *pnpm-lock.yaml)
            echo "pnpm"
            ;;
        *go.mod|*go.sum)
            echo "go"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# Check version in lock file
check_version() {
    local lockfile="$1"
    local package="$2"
    local expected="$3"
    local type="$4"

    case "$type" in
        "uv")
            # Format: [[package]] name = "pkg" version = "1.0.0"
            actual=$(grep -A5 "name = \"${package}\"" "$lockfile" 2>/dev/null | grep -m1 "version = " | sed 's/.*version = "\([^"]*\)".*/\1/' || echo "NOT_FOUND")
            ;;
        "poetry")
            # Format: [[package]] name = "pkg" version = "1.0.0"
            actual=$(grep -A3 "name = \"${package}\"" "$lockfile" 2>/dev/null | grep -m1 "version = " | sed 's/.*version = "\([^"]*\)".*/\1/' || echo "NOT_FOUND")
            ;;
        "npm")
            # JSON format
            actual=$(jq -r ".packages[\"node_modules/${package}\"].version // \"NOT_FOUND\"" "$lockfile" 2>/dev/null || echo "NOT_FOUND")
            ;;
        "yarn")
            # yarn.lock format
            actual=$(grep -A1 "^\"${package}@" "$lockfile" 2>/dev/null | grep "version" | head -1 | sed 's/.*"\([^"]*\)".*/\1/' || echo "NOT_FOUND")
            ;;
        "cargo")
            # Cargo.lock format
            actual=$(grep -A2 "name = \"${package}\"" "$lockfile" 2>/dev/null | grep -m1 "version = " | sed 's/.*version = "\([^"]*\)".*/\1/' || echo "NOT_FOUND")
            ;;
        "go")
            # go.mod format: require pkg v1.0.0
            actual=$(grep "${package}" "$lockfile" 2>/dev/null | grep -oE "v[0-9]+\.[0-9]+\.[0-9]+" | head -1 || echo "NOT_FOUND")
            # Remove 'v' prefix for comparison
            actual="${actual#v}"
            ;;
        *)
            actual="UNKNOWN_TYPE"
            ;;
    esac

    echo "$actual"
}

TYPE=$(detect_type "$LOCKFILE")
echo "Detected type: $TYPE"
echo ""

FAILED=0
echo "| Package | Expected | Actual | Status |"
echo "|---------|----------|--------|--------|"

for pkg_ver in "${PACKAGES[@]}"; do
    IFS=':' read -r package expected <<< "$pkg_ver"

    actual=$(check_version "$LOCKFILE" "$package" "$expected" "$TYPE")

    if [[ "$actual" == "$expected" ]]; then
        echo "| $package | $expected | $actual | ✓ OK |"
    elif [[ "$actual" == "NOT_FOUND" ]]; then
        echo "| $package | $expected | NOT_FOUND | ✗ MISSING |"
        FAILED=$((FAILED + 1))
    else
        echo "| $package | $expected | $actual | ✗ MISMATCH |"
        FAILED=$((FAILED + 1))
    fi
done

echo ""
if [[ $FAILED -eq 0 ]]; then
    echo "✓ All versions verified successfully"
    exit 0
else
    echo "✗ $FAILED package(s) failed verification"
    exit 1
fi
