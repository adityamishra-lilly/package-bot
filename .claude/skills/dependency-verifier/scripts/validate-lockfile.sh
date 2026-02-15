#!/bin/bash
# Script: Validate Lock File
# Purpose: Check that lock file is properly formatted
# Usage: ./validate-lockfile.sh <lockfile>
#
# Returns exit code 0 if valid, 1 otherwise

set -euo pipefail

LOCKFILE="${1:?Usage: $0 <lockfile>}"

echo "=== Lock File Validation ==="
echo "File: $LOCKFILE"
echo ""

if [[ ! -f "$LOCKFILE" ]]; then
    echo "✗ File not found: $LOCKFILE"
    exit 1
fi

# Detect and validate file type
validate_toml() {
    python3 -c "import tomllib; tomllib.load(open('$1', 'rb'))" 2>&1
}

validate_json() {
    python3 -c "import json; json.load(open('$1'))" 2>&1
}

validate_yaml() {
    python3 -c "import yaml; yaml.safe_load(open('$1'))" 2>&1
}

case "$LOCKFILE" in
    *.toml|uv.lock|poetry.lock|Cargo.lock)
        echo "Format: TOML"
        if result=$(validate_toml "$LOCKFILE"); then
            echo "✓ Valid TOML"
            exit 0
        else
            echo "✗ Invalid TOML"
            echo "$result"
            exit 1
        fi
        ;;

    *.json|package-lock.json)
        echo "Format: JSON"
        if result=$(validate_json "$LOCKFILE"); then
            echo "✓ Valid JSON"
            exit 0
        else
            echo "✗ Invalid JSON"
            echo "$result"
            exit 1
        fi
        ;;

    *.yaml|*.yml|pnpm-lock.yaml)
        echo "Format: YAML"
        if result=$(validate_yaml "$LOCKFILE"); then
            echo "✓ Valid YAML"
            exit 0
        else
            echo "✗ Invalid YAML"
            echo "$result"
            exit 1
        fi
        ;;

    yarn.lock)
        echo "Format: Yarn Lock (custom)"
        # Basic validation: check file is not empty and has expected structure
        if [[ -s "$LOCKFILE" ]] && grep -q "^__metadata:" "$LOCKFILE" 2>/dev/null || grep -q "@" "$LOCKFILE"; then
            echo "✓ Valid Yarn lock file"
            exit 0
        else
            echo "✗ Invalid or empty Yarn lock file"
            exit 1
        fi
        ;;

    go.mod)
        echo "Format: Go mod"
        if grep -q "^module " "$LOCKFILE"; then
            echo "✓ Valid go.mod"
            exit 0
        else
            echo "✗ Invalid go.mod - missing module declaration"
            exit 1
        fi
        ;;

    go.sum)
        echo "Format: Go sum"
        # Check for valid checksum lines
        if [[ -s "$LOCKFILE" ]] && head -1 "$LOCKFILE" | grep -qE "^[a-z].*h1:"; then
            echo "✓ Valid go.sum"
            exit 0
        else
            echo "✗ Invalid go.sum format"
            exit 1
        fi
        ;;

    *)
        echo "Unknown file type: $LOCKFILE"
        exit 1
        ;;
esac
