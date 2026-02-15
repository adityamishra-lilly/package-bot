# PR Review Criteria for Security Updates

## Required Elements

### 1. Title Requirements

- Must indicate security nature of update
- Should be clear and descriptive
- Follow conventional commit format if applicable

**Good Examples:**
- `Security: Update vulnerable dependencies`
- `fix(deps): resolve CVE-2025-12345 in lodash`
- `chore(security): patch GHSA-xxxx-xxxx-xxxx`

**Bad Examples:**
- `Update stuff`
- `fixes`
- `WIP`

### 2. CVE/GHSA References

PR body MUST contain:
- CVE identifiers: `CVE-YYYY-NNNNN`
- GHSA identifiers: `GHSA-xxxx-xxxx-xxxx`
- Severity levels (critical/high/medium/low)

### 3. Vulnerability Table

Required format:
```markdown
| Package | From | To | CVE | Severity |
|---------|------|-----|-----|----------|
| lodash | 4.17.0 | 4.17.21 | CVE-2025-12345 | high |
```

### 4. Major Version Warnings

When major version updates present:
- Flag with warning emoji
- List potential breaking changes
- Link to changelog if available
- Note alternative minor versions if exist

### 5. Files Modified Section

List all modified files:
- Lock files (expected)
- Manifest files (may be expected)
- Source files (unexpected - flag for review)

## Validation Checks

### Lock Files Only Rule

For automated security updates:
- ONLY lock files should be modified
- No application code changes
- No configuration changes

### No Sensitive Files

Never include:
- `.env` files
- Credential files
- Private keys
- API tokens

### Formatting

- Tables must render correctly
- Links must be valid
- Markdown syntax must be proper
- Co-Authored-By format must be correct

## Review Outcomes

| Outcome | Criteria |
|---------|----------|
| APPROVED | All checks pass, ready to merge |
| CHANGES_REQUESTED | Issues found that must be fixed |
| PENDING | Cannot complete review, needs info |
