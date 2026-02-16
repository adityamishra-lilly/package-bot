#!/bin/bash
# review-ticket.sh - Helper script for reviewing Jira tickets
#
# Usage: review-ticket.sh <issue_key>
#
# This script is a reference for the Jira ticket review workflow.
# The actual review is done via mcp__jira__get_issue and mcp__jira__update_issue.

set -euo pipefail

ISSUE_KEY="${1:?Usage: review-ticket.sh <issue_key>}"

echo "Reviewing Jira ticket: ${ISSUE_KEY}"
echo ""
echo "Review checklist:"
echo "  [ ] Summary follows format: Review PR #N: Security dependency updates for repo"
echo "  [ ] Description contains PR link"
echo "  [ ] Description contains vulnerability table"
echo "  [ ] Description contains CVE/GHSA references"
echo "  [ ] Description contains severity summary"
echo "  [ ] Description contains major version warnings (if applicable)"
echo "  [ ] Priority matches highest severity"
echo "  [ ] Labels include: security, dependabot, automated"
echo "  [ ] Issue type is Bug"
echo "  [ ] Action items checklist present"
echo ""
echo "Use mcp__jira__get_issue to fetch ticket details for review."
echo "Use mcp__jira__update_issue to fix any issues found."
