#!/bin/bash
# Script: Update Python Package
# Purpose: Update a Python package using uv or poetry
# Usage: ./update-pip.sh <package> <version> [uv|poetry]
#
# Automatically detects package manager if not specified

set -euo pipefail

PACKAGE="${1:?Usage: $0 <package> <version> [uv|poetry]}"
VERSION="${2:?Usage: $0 <package> <version> [uv|poetry]}"
MANAGER="${3:-auto}"

# Auto-detect package manager
detect_manager() {
    if [[ -f "uv.lock" ]]; then
        echo "uv"
    elif [[ -f "poetry.lock" ]]; then
        echo "poetry"
    elif [[ -f "pyproject.toml" ]]; then
        if grep -q "\[tool.uv\]" pyproject.toml 2>/dev/null; then
            echo "uv"
        elif grep -q "\[tool.poetry\]" pyproject.toml 2>/dev/null; then
            echo "poetry"
        else
            echo "uv"  # Default to uv for pyproject.toml
        fi
    else
        echo "unknown"
    fi
}

if [[ "$MANAGER" == "auto" ]]; then
    MANAGER=$(detect_manager)
    echo "Detected package manager: $MANAGER"
fi

echo "=== Update Python Package ==="
echo "Package: $PACKAGE"
echo "Version: $VERSION"
echo "Manager: $MANAGER"
echo ""

case "$MANAGER" in
    "uv")
        echo "Running: uv lock --upgrade-package ${PACKAGE}==${VERSION}"
        uv lock --upgrade-package "${PACKAGE}==${VERSION}"

        # Verify update
        echo ""
        echo "Verifying update in uv.lock..."
        if grep -q "name = \"${PACKAGE}\"" uv.lock && grep -A5 "name = \"${PACKAGE}\"" uv.lock | grep -q "version = \"${VERSION}\""; then
            echo "✓ Package updated successfully"
        else
            echo "⚠ Warning: Could not verify package version in lock file"
        fi
        ;;

    "poetry")
        echo "Running: poetry update ${PACKAGE}@${VERSION} --lock"
        poetry update "${PACKAGE}@${VERSION}" --lock

        # Verify update
        echo ""
        echo "Verifying update in poetry.lock..."
        if grep -A3 "name = \"${PACKAGE}\"" poetry.lock | grep -q "version = \"${VERSION}\""; then
            echo "✓ Package updated successfully"
        else
            echo "⚠ Warning: Could not verify package version in lock file"
        fi
        ;;

    *)
        echo "Error: Unknown package manager: $MANAGER"
        echo "Supported: uv, poetry"
        exit 1
        ;;
esac

echo ""
echo "=== Files Modified ==="
git status --short
