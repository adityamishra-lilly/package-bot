#!/bin/bash
# create-ticket.sh - Helper script for creating Jira tickets for security PRs
#
# Usage: create-ticket.sh <project_key> <pr_number> <repo_name> <priority>
#
# This script is a reference for the Jira ticket creation workflow.
# The actual creation is done via mcp__jira__create_issue.

set -euo pipefail

PROJECT_KEY="${1:?Usage: create-ticket.sh <project_key> <pr_number> <repo_name> <priority>}"
PR_NUMBER="${2:?Missing PR number}"
REPO_NAME="${3:?Missing repo name}"
PRIORITY="${4:-Medium}"

echo "Creating Jira ticket..."
echo "  Project: ${PROJECT_KEY}"
echo "  PR: #${PR_NUMBER}"
echo "  Repository: ${REPO_NAME}"
echo "  Priority: ${PRIORITY}"
echo ""
echo "Summary: Review PR #${PR_NUMBER}: Security dependency updates for ${REPO_NAME}"
echo "Type: Bug"
echo "Labels: security, dependabot, automated"
echo ""
echo "Use mcp__jira__create_issue to create the ticket with the full description."
