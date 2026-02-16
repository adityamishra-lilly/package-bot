# Jira Ticket Review Criteria

## Required Fields

### Summary
- **Format**: `Review PR #{pr_number}: Security dependency updates for {repo_name}`
- **Max length**: 255 characters
- **Must contain**: PR number and repository name

### Description
Must include ALL of the following sections:

1. **PR Link**: Full GitHub PR URL
2. **Repository**: `org/repo_name` format
3. **Branch**: Fix branch name
4. **Vulnerability Table**: Package, from, to, CVE, severity, CVSS columns
5. **Severity Summary**: Count of each severity level
6. **Major Version Warnings**: If any major version updates exist
7. **Action Items**: Review checklist

### Priority
Must match the highest severity across all vulnerabilities:

| Highest Severity | Expected Priority |
|-----------------|-------------------|
| critical | Highest |
| high | High |
| medium | Medium |
| low | Low |

### Labels
Must include exactly: `["security", "dependabot", "automated"]`

### Issue Type
Must be `Bug`

## Quality Standards

### Vulnerability Table Completeness
- Every security alert should have a row
- CVE/GHSA identifiers must be present
- CVSS scores should be included
- Severity levels must match the vulnerability data

### Major Version Updates
If any packages have major version bumps (e.g., 1.x → 2.x):
- Must be prominently flagged
- Warning about breaking changes must be included
- Listed separately from the vulnerability table

### Action Items
Must include actionable review steps:
- Review PR changes
- Verify no breaking changes
- Run tests if applicable
- Approve or request changes
- Merge when ready

## Scoring

| Category | Weight | Pass Criteria |
|----------|--------|---------------|
| Summary format | 15% | Matches expected format |
| PR link present | 15% | Valid GitHub PR URL |
| Vulnerability table | 20% | All alerts represented |
| CVE references | 15% | All CVEs/GHSAs listed |
| Priority correct | 10% | Matches highest severity |
| Labels correct | 10% | All three labels present |
| Major version warnings | 10% | Flagged if applicable |
| Action items | 5% | Checklist present |

## Auto-Fix Guidelines

The reviewer should auto-fix these issues:
- Missing labels → Add via update_issue
- Wrong priority → Correct via update_issue
- Incomplete description → Rewrite via update_issue
- Missing severity summary → Add to description

The reviewer should NOT auto-fix:
- Wrong project (requires delete + recreate)
- Invalid PR link (needs manual verification)
- Missing vulnerability data (not available to reviewer)
