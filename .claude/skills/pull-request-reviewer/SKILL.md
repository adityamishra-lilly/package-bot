---
name: pull-request-reviewer
description: Reviews pull requests for security updates. Use when you need to validate PR quality, check CVE references, and verify proper documentation.
allowed-tools: Read, Bash, Grep, Glob, WebFetch, TodoWrite
---

# Pull Request Reviewer

## Core Workflow

Every PR review follows this pattern:

1. **Fetch**: Get PR details via github-mcp
2. **Check**: Validate against quality checklist
3. **Verify**: Ensure security requirements met
4. **Report**: Provide approval status

```bash
# Step 1: Get PR details
mcp__github__get_pull_request owner repo pr_number

# Step 2: Check PR diff
mcp__github__get_pull_request_diff owner repo pr_number

# Step 3: Review against checklist
# ... (automated checks)

# Step 4: Generate report
```

## Review Checklist

### Title and Description
- [ ] Title clearly indicates security update
- [ ] Description includes vulnerability table
- [ ] CVE/GHSA identifiers listed
- [ ] Severity levels documented
- [ ] Files modified listed

### Major Version Updates
- [ ] Major updates flagged with ⚠️
- [ ] Breaking change warnings included
- [ ] Changelog links provided (if available)

### Code Changes
- [ ] Only lock files modified
- [ ] No application code changes
- [ ] No sensitive files (*.env, credentials, etc.)
- [ ] No unrelated changes

### Formatting
- [ ] Markdown renders correctly
- [ ] Tables display properly
- [ ] Links are valid
- [ ] Co-Authored-By format correct

## Automated Checks

### Check 1: Title Format
```bash
# Good titles
"Security: Update vulnerable dependencies"
"fix(deps): resolve CVE-2025-12345"

# Bad titles
"Update stuff"
"fixes"
```

### Check 2: CVE References
```bash
# Must contain CVE or GHSA references
grep -E "(CVE-[0-9]{4}-[0-9]+|GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4})" pr_body
```

### Check 3: Lock Files Only
```bash
# Check diff only contains lock files
git diff --name-only | grep -vE "\.(lock|json)$"
# Should return empty
```

### Check 4: No Sensitive Files
```bash
# Ensure no sensitive files in diff
git diff --name-only | grep -E "\.(env|secret|key|pem)$"
# Should return empty
```

## Ready-to-Use Scripts

| Script | Description |
|--------|-------------|
| [scripts/review-pr.sh](scripts/review-pr.sh) | Automated PR review |
| [scripts/check-diff.sh](scripts/check-diff.sh) | Validate PR diff |

## Output Report Format

```markdown
## PR Review Report

### PR: #123 - Security: Update vulnerable dependencies

### Status: ✓ APPROVED | ⚠️ CHANGES_REQUESTED | ⏳ PENDING

### Checklist Results

| Category | Item | Status |
|----------|------|--------|
| Title | Clear security title | ✓ |
| Description | CVE references | ✓ |
| Description | Severity levels | ✓ |
| Description | Major version warnings | ✓ |
| Changes | Lock files only | ✓ |
| Changes | No sensitive files | ✓ |
| Format | Proper markdown | ✓ |

### Issues Found

- None

### Recommendation

**APPROVE**: This PR meets all security update standards and is ready to merge.

### Merge Notes

- Review major version updates if flagged
- Run CI/CD pipeline before merge
- Consider squash merge for clean history
```

## Review Outcomes

### APPROVED
PR meets all requirements:
- Clear title and description
- All CVEs documented
- Only expected files changed
- Proper formatting

### CHANGES_REQUESTED
Issues found that must be fixed:
- Missing CVE references
- Major version not documented
- Unexpected file changes
- Formatting issues

### PENDING
Cannot complete review:
- PR not accessible
- Missing information
- Requires manual verification

## References

| Reference | When to Use |
|-----------|-------------|
| [references/review-criteria.md](references/review-criteria.md) | Review standards |
