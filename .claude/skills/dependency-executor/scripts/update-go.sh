#!/bin/bash
# Script: Update Go Module
# Purpose: Update a Go module dependency
# Usage: ./update-go.sh <module> <version>

set -euo pipefail

MODULE="${1:?Usage: $0 <module> <version>}"
VERSION="${2:?Usage: $0 <module> <version>}"

# Ensure version has 'v' prefix
if [[ ! "$VERSION" =~ ^v ]]; then
    VERSION="v${VERSION}"
fi

echo "=== Update Go Module ==="
echo "Module: $MODULE"
echo "Version: $VERSION"
echo ""

# Check for go.mod
if [[ ! -f "go.mod" ]]; then
    echo "Error: go.mod not found"
    exit 1
fi

# Get the module
echo "Running: go get ${MODULE}@${VERSION}"
go get "${MODULE}@${VERSION}"

# Tidy up
echo "Running: go mod tidy"
go mod tidy

# Verify update in go.mod
echo ""
echo "Verifying update in go.mod..."
if grep -q "${MODULE} ${VERSION}" go.mod; then
    echo "✓ Module updated successfully"
else
    echo "⚠ Warning: Could not verify exact version in go.mod"
    echo "Current entry:"
    grep "${MODULE}" go.mod || echo "Module not found in go.mod"
fi

# Check go.sum
echo ""
echo "Verifying update in go.sum..."
if [[ -f "go.sum" ]] && grep -q "${MODULE} ${VERSION}" go.sum; then
    echo "✓ Checksum added to go.sum"
else
    echo "⚠ Warning: Could not verify checksum in go.sum"
fi

echo ""
echo "=== Files Modified ==="
git status --short
