# PR Field Evaluation Criteria

## Title Requirements

- Must indicate security nature of update
- Must be clear and descriptive
- Follow conventional commit format if applicable

**Correct:**
- `Security: Update vulnerable dependencies`
- `fix(deps): resolve CVE-2025-12345 in lodash`
- `chore(security): patch GHSA-xxxx-xxxx-xxxx`

**Incorrect (update these):**
- `Update stuff`
- `fixes`
- `WIP`

## Body Requirements

### 1. Vulnerability Table

Must contain a properly formatted table:
```markdown
| Package | From | To | CVE | Severity |
|---------|------|-----|-----|----------|
| lodash | 4.17.0 | 4.17.21 | CVE-2025-12345 | high |
```

### 2. CVE/GHSA References

Body must contain:
- CVE identifiers: `CVE-YYYY-NNNNN`
- GHSA identifiers: `GHSA-xxxx-xxxx-xxxx`
- Severity levels (critical/high/medium/low)

### 3. Major Version Warnings

When major version updates are present:
- Flag with warning emoji
- List potential breaking changes
- Link to changelog if available
- Note alternative minor versions if they exist

### 4. Files Modified Section

List all modified files:
- Lock files (expected)
- Manifest files (may be expected)
- Source files (unexpected - include a note)

### 5. Formatting

- Tables must render correctly
- Links must be valid
- Markdown syntax must be proper
- Co-Authored-By format must be correct

## Diff Validation

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
