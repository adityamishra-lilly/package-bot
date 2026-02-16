---
name: jira-ticket-creator
description: Creates Jira Bug issues to track review of security PRs. Use when you need to create a Jira ticket with vulnerability details, PR link, severity-based priority, and proper labels.
allowed-tools: Read, Bash, Grep, Glob, TodoWrite
---

# Jira Ticket Creator

## Core Workflow

Every Jira ticket creation follows this pattern:

1. **Gather**: Collect PR details, vulnerability data, and severity information
2. **Map Priority**: Convert highest severity to Jira priority
3. **Format**: Build issue description with vulnerability table and PR link
4. **Create**: Submit Bug issue via `mcp__jira__create_issue`
5. **Verify**: Confirm ticket was created successfully

```bash
# Step 1: Gather PR and vulnerability info
# PR URL, PR number, repo name, vulnerability data are provided in context

# Step 2: Map severity to Jira priority
# critical → Highest
# high → High
# medium → Medium
# low → Low

# Step 3: Create issue via Jira MCP
mcp__jira__create_issue {
  "project_key": "PROJECT",
  "issue_type": "Bug",
  "summary": "Review PR #123: Security dependency updates for repo-name",
  "description": "... (plain text, converted to ADF internally)",
  "priority": "High",
  "labels": ["security", "dependabot", "automated"]
}
```

## Priority Mapping

| Highest Severity | Jira Priority |
|-----------------|---------------|
| critical | Highest |
| high | High |
| medium | Medium |
| low | Low |

## Issue Description Template

The description should include the following sections in plain text (the Jira MCP converts to ADF internally):

```
Security PR Review Required

PR: https://github.com/org/repo/pull/123
Repository: org/repo
Branch: fix/security-alerts-XXXXXXXX

Vulnerabilities Fixed:

| Package | From | To | CVE | Severity | CVSS |
|---------|------|-----|-----|----------|------|
| virtualenv | 20.0.0 | 20.28.1 | CVE-2025-68146 | medium | 5.3 |

Severity Summary:
- Critical: 0
- High: 1
- Medium: 2
- Low: 0

Major Version Updates (if any):
- WARNING: containerd 1.6.0 -> 2.2.0 (major version - breaking changes possible)

Action Items:
- [ ] Review PR changes
- [ ] Verify no breaking changes from major version updates
- [ ] Run integration tests if applicable
- [ ] Approve or request changes on PR
- [ ] Merge PR when ready

Generated automatically by Packagebot
```

## Important Notes

- **Plain text only**: The Jira MCP accepts plain text and converts to Atlassian Document Format internally
- **Labels**: Always include `["security", "dependabot", "automated"]`
- **Issue type**: Always use `Bug`
- **Summary format**: `Review PR #{pr_number}: Security dependency updates for {repo_name}`
- **Major version warnings**: Include prominently if any major version updates exist

## Ready-to-Use Scripts

| Script | Description |
|--------|-------------|
| [scripts/create-ticket.sh](scripts/create-ticket.sh) | Create Jira ticket helper |

## Templates

| Template | Description |
|----------|-------------|
| [templates/issue-template.md](templates/issue-template.md) | Full issue description template |

## References

| Reference | When to Use |
|-----------|-------------|
| [references/jira-fields.md](references/jira-fields.md) | Jira field reference |

## Output Format

After ticket creation, report:

```markdown
## Jira Ticket Created Successfully

- **Key**: PROJ-456
- **URL**: https://yourteam.atlassian.net/browse/PROJ-456
- **Summary**: Review PR #123: Security dependency updates for repo-name
- **Priority**: High
- **Labels**: security, dependabot, automated
- **Status**: Created in backlog
```

## Common Mistakes

### Using HTML or ADF in Description
The Jira MCP accepts plain text only. Do not use HTML tags or ADF JSON.

### Missing PR Link
Always include the full PR URL so reviewers can navigate directly.

### Wrong Priority Mapping
Map from the HIGHEST severity across all vulnerabilities, not individual ones.

### Forgetting Major Version Warnings
Major version updates should be prominently flagged in the description.
