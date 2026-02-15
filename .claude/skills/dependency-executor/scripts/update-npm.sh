#!/bin/bash
# Script: Update Node.js Package
# Purpose: Update a Node.js package using npm, yarn, or pnpm
# Usage: ./update-npm.sh <package> <version> [npm|yarn|pnpm]
#
# Automatically detects package manager if not specified

set -euo pipefail

PACKAGE="${1:?Usage: $0 <package> <version> [npm|yarn|pnpm]}"
VERSION="${2:?Usage: $0 <package> <version> [npm|yarn|pnpm]}"
MANAGER="${3:-auto}"

# Auto-detect package manager
detect_manager() {
    if [[ -f "pnpm-lock.yaml" ]]; then
        echo "pnpm"
    elif [[ -f "yarn.lock" ]]; then
        echo "yarn"
    elif [[ -f "package-lock.json" ]]; then
        echo "npm"
    else
        echo "npm"  # Default to npm
    fi
}

if [[ "$MANAGER" == "auto" ]]; then
    MANAGER=$(detect_manager)
    echo "Detected package manager: $MANAGER"
fi

echo "=== Update Node.js Package ==="
echo "Package: $PACKAGE"
echo "Version: $VERSION"
echo "Manager: $MANAGER"
echo ""

case "$MANAGER" in
    "npm")
        echo "Running: npm install ${PACKAGE}@${VERSION} --package-lock-only"
        npm install "${PACKAGE}@${VERSION}" --package-lock-only

        # Verify update
        echo ""
        echo "Verifying update in package-lock.json..."
        if grep -q "\"${PACKAGE}\": {" package-lock.json && grep -A2 "\"${PACKAGE}\":" package-lock.json | grep -q "\"${VERSION}\""; then
            echo "✓ Package updated successfully"
        else
            echo "⚠ Warning: Could not verify package version in lock file"
        fi
        ;;

    "yarn")
        echo "Running: yarn add ${PACKAGE}@${VERSION} --mode update-lockfile"
        yarn add "${PACKAGE}@${VERSION}" --mode update-lockfile

        # Verify update
        echo ""
        echo "Verifying update in yarn.lock..."
        if grep -q "${PACKAGE}@${VERSION}" yarn.lock; then
            echo "✓ Package updated successfully"
        else
            echo "⚠ Warning: Could not verify package version in lock file"
        fi
        ;;

    "pnpm")
        echo "Running: pnpm update ${PACKAGE}@${VERSION} --lockfile-only"
        pnpm update "${PACKAGE}@${VERSION}" --lockfile-only

        # Verify update
        echo ""
        echo "Verifying update in pnpm-lock.yaml..."
        if grep -q "${PACKAGE}:" pnpm-lock.yaml && grep -A5 "${PACKAGE}:" pnpm-lock.yaml | grep -q "${VERSION}"; then
            echo "✓ Package updated successfully"
        else
            echo "⚠ Warning: Could not verify package version in lock file"
        fi
        ;;

    *)
        echo "Error: Unknown package manager: $MANAGER"
        echo "Supported: npm, yarn, pnpm"
        exit 1
        ;;
esac

echo ""
echo "=== Files Modified ==="
git status --short
