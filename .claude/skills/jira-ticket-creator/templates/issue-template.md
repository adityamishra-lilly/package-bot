# Jira Bug Issue Template for Security PR Review

## Summary Format

```
Review PR #{{PR_NUMBER}}: Security dependency updates for {{REPO_NAME}}
```

## Description Template

```
Security PR Review Required

PR: {{PR_URL}}
Repository: {{ORG}}/{{REPO_NAME}}
Branch: {{BRANCH_NAME}}

Vulnerabilities Fixed:

| Package | From | To | CVE | Severity | CVSS |
|---------|------|-----|-----|----------|------|
{{#each VULNERABILITIES}}
| {{PACKAGE}} | {{CURRENT_VERSION}} | {{TARGET_VERSION}} | {{CVE}} | {{SEVERITY}} | {{CVSS}} |
{{/each}}

Severity Summary:
- Critical: {{CRITICAL_COUNT}}
- High: {{HIGH_COUNT}}
- Medium: {{MEDIUM_COUNT}}
- Low: {{LOW_COUNT}}

{{#if MAJOR_VERSION_UPDATES}}
Major Version Updates:
{{#each MAJOR_VERSION_UPDATES}}
- WARNING: {{PACKAGE}} {{CURRENT}} -> {{TARGET}} (major version - breaking changes possible)
{{/each}}

Please pay special attention to major version updates during review.
Breaking changes may require additional testing or code modifications.
{{/if}}

Action Items:
- [ ] Review PR changes
- [ ] Verify no breaking changes from major version updates
- [ ] Run integration tests if applicable
- [ ] Approve or request changes on PR
- [ ] Merge PR when ready

Generated automatically by Packagebot
```

## Field Mapping

| Field | Value |
|-------|-------|
| Project | `{{PROJECT_KEY}}` |
| Issue Type | Bug |
| Summary | `Review PR #{{PR_NUMBER}}: Security dependency updates for {{REPO_NAME}}` |
| Priority | Mapped from highest severity |
| Labels | `["security", "dependabot", "automated"]` |
| Description | See template above |

## Priority Mapping

| Highest Severity | Jira Priority |
|-----------------|---------------|
| critical | Highest |
| high | High |
| medium | Medium |
| low | Low |
