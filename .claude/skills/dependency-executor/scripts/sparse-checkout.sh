#!/bin/bash
# Script: Sparse Checkout
# Purpose: Clone repository with minimal files using sparse checkout
# Usage: ./sparse-checkout.sh <repo-url> <file1> [file2] [file3] ...
#
# Creates a sparse checkout in ./repo subdirectory with only specified files
# Uses --filter=blob:none for minimal network transfer

set -euo pipefail

REPO_URL="${1:?Usage: $0 <repo-url> <file1> [file2] ...}"
shift
FILES=("$@")

if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "Error: At least one file path required"
    exit 1
fi

echo "=== Sparse Checkout ==="
echo "Repository: $REPO_URL"
echo "Files: ${FILES[*]}"
echo ""

# Clean up existing repo directory
if [[ -d "repo" ]]; then
    echo "Removing existing repo directory..."
    rm -rf repo
fi

# Clone with no checkout and blob filter
echo "Cloning repository (no checkout)..."
git clone --no-checkout --filter=blob:none "$REPO_URL" repo

cd repo

# Create fix branch with timestamp
BRANCH_NAME="fix/security-alerts-$(date +%Y%m%d-%H%M%S)"
echo "Creating branch: $BRANCH_NAME"
git checkout -b "$BRANCH_NAME"

# Initialize sparse checkout in no-cone mode (better cross-platform support)
echo "Configuring sparse checkout..."
git sparse-checkout init --no-cone

# Set files to checkout (use forward slashes even on Windows)
# Convert backslashes to forward slashes for Windows compatibility
NORMALIZED_FILES=()
for file in "${FILES[@]}"; do
    NORMALIZED_FILES+=("${file//\\//}")
done

git sparse-checkout set "${NORMALIZED_FILES[@]}"

# Perform checkout
echo "Checking out files..."
git checkout

# Verify files exist
echo ""
echo "=== Verification ==="
MISSING=0
for file in "${NORMALIZED_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✓ $file"
    else
        echo "✗ $file (MISSING)"
        MISSING=$((MISSING + 1))
    fi
done

if [[ $MISSING -gt 0 ]]; then
    echo ""
    echo "Warning: $MISSING file(s) not found in repository"
    exit 1
fi

echo ""
echo "=== Complete ==="
echo "Branch: $BRANCH_NAME"
echo "Working directory: $(pwd)"
echo "Files checked out: ${#NORMALIZED_FILES[@]}"
