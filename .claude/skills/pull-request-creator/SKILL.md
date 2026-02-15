---
name: pull-request-creator
description: Creates well-formatted pull requests for security updates. Use when you need to create a PR with vulnerability details, CVE references, and proper formatting.
allowed-tools: Read, Bash, Grep, Glob, TodoWrite
---

# Pull Request Creator

## Core Workflow

Every PR creation follows this pattern:

1. **Gather**: Collect vulnerability and change information
2. **Format**: Build PR description with proper structure
3. **Create**: Submit PR via github-mcp
4. **Verify**: Confirm PR was created successfully

```bash
# Step 1: Get branch info
git branch --show-current
git log -1 --oneline

# Step 2: Read vulnerability data
cat vulnerability-object.json

# Step 3: Create PR via github-mcp
mcp__github__create_pull_request {
  "owner": "org",
  "repo": "repo",
  "title": "Security: Update vulnerable dependencies",
  "body": "## Security Remediation\n\n...",
  "head": "fix/security-alerts-XXXXXXXX",
  "base": "main"
}
```

## ⚠️ CRITICAL: PR Body Formatting

**The PR body MUST use actual newlines, NOT escaped `\n` characters.**

### ❌ WRONG - Using \n escape sequences:
```json
{
  "body": "## Security Remediation\n\nThis PR updates...\n\n## Vulnerabilities"
}
```
This renders as literal `\n` text in GitHub!

### ✅ RIGHT - Using actual newlines:
```json
{
  "body": "## Security Remediation

This PR updates vulnerable dependencies.

## Vulnerabilities Fixed

| Package | Version | CVE |
|---------|---------|-----|
| pkg | 1.0.0 | CVE-2025-12345 |"
}
```

## PR Template

```markdown
## Security Remediation

This PR updates vulnerable dependencies identified by Dependabot alerts.

### Vulnerabilities Fixed

| Package | From | To | CVE | Severity |
|---------|------|-----|-----|----------|
| {{PACKAGE}} | {{OLD_VERSION}} | {{NEW_VERSION}} | {{CVE}} | {{SEVERITY}} |

### Changes Made

- Updated lock files only (no application code changes)
- No full installs performed
- Minimal file modifications

### Major Version Updates ⚠️

{{#if MAJOR_UPDATES}}
The following packages have major version bumps - review for breaking changes:
{{#each MAJOR_UPDATES}}
- **{{PACKAGE}}**: {{OLD}} → {{NEW}}
{{/each}}
{{else}}
No major version updates in this PR.
{{/if}}

### Files Modified

{{#each FILES}}
- {{FILE}}
{{/each}}

### Verification

- [ ] All packages updated to expected versions
- [ ] Lock files valid
- [ ] No unintended changes

---

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Ready-to-Use Templates

| Template | Description |
|----------|-------------|
| [templates/create-pr.sh](templates/create-pr.sh) | Create PR with formatting |
| [templates/build-description.sh](templates/build-description.sh) | Generate PR body |

## Usage Examples

### Basic PR Creation
```bash
./templates/create-pr.sh org repo fix/security-alerts-20260215 main
```

### With Vulnerability Data
```bash
./templates/build-description.sh vulnerability-object.json > pr-body.md
./templates/create-pr.sh org repo fix/security-alerts-20260215 main pr-body.md
```

## Common Mistakes

### Escaped Newlines
The most common error - using `\n` instead of actual newlines.

### Missing CVE References
Always include CVE and GHSA identifiers from the vulnerability data.

### Forgetting Major Version Warnings
Major version updates should be prominently flagged.

### Wrong Co-Authored-By Format
Use: `Co-Authored-By: Claude <noreply@anthropic.com>`
NOT: `Co-Authored-By: Claude noreply@anthropic.com`

## Output Format

After PR creation, report:

```markdown
## PR Created Successfully

- **URL**: https://github.com/org/repo/pull/123
- **Number**: #123
- **Title**: Security: Update vulnerable dependencies
- **Branch**: fix/security-alerts-20260215 → main
- **Status**: Open
```

## References

| Reference | When to Use |
|-----------|-------------|
| [PR-template.md](PR-template.md) | Full PR template |
