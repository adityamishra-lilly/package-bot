#!/bin/bash
# Script: Update Rust Package
# Purpose: Update a Rust crate using cargo
# Usage: ./update-cargo.sh <package> <version>

set -euo pipefail

PACKAGE="${1:?Usage: $0 <package> <version>}"
VERSION="${2:?Usage: $0 <package> <version>}"

echo "=== Update Rust Package ==="
echo "Package: $PACKAGE"
echo "Version: $VERSION"
echo ""

# Check for Cargo.toml
if [[ ! -f "Cargo.toml" ]]; then
    echo "Error: Cargo.toml not found"
    exit 1
fi

# Update the package
echo "Running: cargo update -p ${PACKAGE}@${VERSION}"
cargo update -p "${PACKAGE}@${VERSION}"

# Verify update in Cargo.lock
echo ""
echo "Verifying update in Cargo.lock..."
if [[ -f "Cargo.lock" ]]; then
    if grep -A2 "name = \"${PACKAGE}\"" Cargo.lock | grep -q "version = \"${VERSION}\""; then
        echo "✓ Package updated successfully"
    else
        echo "⚠ Warning: Could not verify package version in lock file"
        echo "Current versions found:"
        grep -A2 "name = \"${PACKAGE}\"" Cargo.lock || echo "Package not found in lock file"
    fi
else
    echo "⚠ Warning: Cargo.lock not found"
fi

echo ""
echo "=== Files Modified ==="
git status --short
