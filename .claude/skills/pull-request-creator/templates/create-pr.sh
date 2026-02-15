#!/bin/bash
# Template: Create Pull Request
# Purpose: Create a PR with proper formatting
# Usage: ./create-pr.sh <owner> <repo> <head-branch> <base-branch> [body-file]
#
# If body-file is provided, uses its content. Otherwise, generates from git log.

set -euo pipefail

OWNER="${1:?Usage: $0 <owner> <repo> <head-branch> <base-branch> [body-file]}"
REPO="${2:?Usage: $0 <owner> <repo> <head-branch> <base-branch> [body-file]}"
HEAD="${3:?Usage: $0 <owner> <repo> <head-branch> <base-branch> [body-file]}"
BASE="${4:?Usage: $0 <owner> <repo> <head-branch> <base-branch> [body-file]}"
BODY_FILE="${5:-}"

echo "=== Create Pull Request ==="
echo "Owner: $OWNER"
echo "Repo: $REPO"
echo "Head: $HEAD"
echo "Base: $BASE"
echo ""

# Generate title from branch name
if [[ "$HEAD" =~ ^fix/security-alerts ]]; then
    TITLE="Security: Update vulnerable dependencies"
else
    TITLE="chore: Update dependencies"
fi

# Generate or read body
if [[ -n "$BODY_FILE" ]] && [[ -f "$BODY_FILE" ]]; then
    BODY=$(cat "$BODY_FILE")
else
    # Generate from git log
    COMMITS=$(git log "$BASE..$HEAD" --oneline 2>/dev/null || echo "No commits found")

    BODY="## Security Remediation

This PR updates vulnerable dependencies.

### Commits

\`\`\`
$COMMITS
\`\`\`

### Changes Made

- Updated lock files
- Security vulnerabilities fixed

---

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
fi

echo "Title: $TITLE"
echo ""
echo "Body preview:"
echo "---"
echo "$BODY" | head -20
echo "---"
echo ""

# Push branch first (if not already pushed)
echo "Ensuring branch is pushed..."
git push -u origin "$HEAD" 2>/dev/null || echo "Branch already pushed or push failed"

echo ""
echo "Creating PR..."
echo "Use github-mcp create_pull_request with:"
echo "  owner: $OWNER"
echo "  repo: $REPO"
echo "  title: $TITLE"
echo "  head: $HEAD"
echo "  base: $BASE"
echo "  body: (see above)"

# Note: Actual PR creation should be done via github-mcp
# This script prepares the data for the agent to use
