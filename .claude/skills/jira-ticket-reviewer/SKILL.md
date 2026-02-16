---
name: jira-ticket-reviewer
description: Reviews Jira tickets created for security PR tracking. Validates ticket quality, completeness, and can fix issues directly via update_issue.
allowed-tools: Read, Bash, Grep, Glob, WebFetch, TodoWrite
---

# Jira Ticket Reviewer

## Core Workflow

Every Jira ticket review follows this pattern:

1. **Fetch**: Get ticket details via `mcp__jira__get_issue`
2. **Check**: Validate against quality checklist
3. **Verify**: Ensure all required information is present
4. **Fix**: Update ticket if issues found (via `mcp__jira__update_issue`)
5. **Report**: Provide review status

```bash
# Step 1: Get ticket details
mcp__jira__get_issue PROJ-456

# Step 2: Validate against checklist
# ... (automated checks)

# Step 3: Fix issues if found
mcp__jira__update_issue PROJ-456 {
  "description": "... corrected description ..."
}

# Step 4: Generate report
```

## Review Checklist

### Summary Quality
- [ ] Follows format: `Review PR #{number}: Security dependency updates for {repo}`
- [ ] Contains PR number
- [ ] Contains repository name
- [ ] Under 255 characters

### Description Completeness
- [ ] PR link included and valid
- [ ] Repository identified
- [ ] Branch name included
- [ ] Vulnerability table present
- [ ] All CVE/GHSA identifiers listed
- [ ] Severity levels documented
- [ ] CVSS scores included
- [ ] Severity summary counts present

### Major Version Updates
- [ ] Major version updates flagged (if applicable)
- [ ] Breaking change warnings included
- [ ] Listed prominently in description

### Metadata
- [ ] Priority matches highest severity
- [ ] Labels include: security, dependabot, automated
- [ ] Issue type is Bug
- [ ] Assigned to correct project

### Action Items
- [ ] Review checklist included
- [ ] Action items are actionable
- [ ] Integration test reminder (if major updates)

## Self-Correction

If issues are found, the reviewer can fix them directly:

### Fix Description
```
mcp__jira__update_issue(
  issue_key: "PROJ-456",
  description: "... corrected description with missing fields ..."
)
```

### Fix Priority
```
mcp__jira__update_issue(
  issue_key: "PROJ-456",
  priority: "High"  # Corrected from Medium
)
```

### Fix Labels
```
mcp__jira__update_issue(
  issue_key: "PROJ-456",
  labels: ["security", "dependabot", "automated"]
)
```

## Ready-to-Use Scripts

| Script | Description |
|--------|-------------|
| [scripts/review-ticket.sh](scripts/review-ticket.sh) | Automated ticket review |

## References

| Reference | When to Use |
|-----------|-------------|
| [references/review-criteria.md](references/review-criteria.md) | Review standards |

## Output Report Format

```markdown
## Jira Ticket Review Report

### Ticket: PROJ-456 - Review PR #123: Security dependency updates for repo-name

### Status: APPROVED | FIXED | CHANGES_REQUESTED

### Checklist Results

| Category | Item | Status |
|----------|------|--------|
| Summary | Correct format | ✓ |
| Summary | PR number present | ✓ |
| Description | PR link included | ✓ |
| Description | Vulnerability table | ✓ |
| Description | CVE references | ✓ |
| Description | Severity summary | ✓ |
| Description | Major version warnings | ✓ |
| Metadata | Priority matches severity | ✓ |
| Metadata | Labels correct | ✓ |
| Metadata | Issue type is Bug | ✓ |
| Action Items | Review checklist | ✓ |

### Issues Found

- None (or list issues and corrections made)

### Recommendation

- APPROVED: Ticket meets all quality standards
- FIXED: Issues found and corrected via update_issue
- CHANGES_REQUESTED: Issues found that require manual intervention
```

## Review Outcomes

### APPROVED
Ticket meets all requirements - no changes needed.

### FIXED
Issues were found and automatically corrected via `mcp__jira__update_issue`.
The reviewer reports what was changed.

### CHANGES_REQUESTED
Issues found that cannot be auto-fixed:
- Wrong project
- Missing vulnerability data (not available)
- PR link points to non-existent PR
