# Jira Field Reference

## Standard Fields Used

### Project Key
- The Jira project to create the issue in
- Example: `SEC`, `DEPS`, `OPS`
- Provided via agent configuration or environment

### Issue Type
- Always use `Bug` for security PR review tickets
- Bug is appropriate because these track security vulnerabilities that need review

### Summary
- Max 255 characters
- Format: `Review PR #{number}: Security dependency updates for {repo_name}`
- Keep concise but descriptive

### Description
- Plain text input (Jira MCP converts to ADF internally)
- Use simple markdown-like formatting
- Tables use pipe `|` syntax
- Checkboxes use `- [ ]` syntax

### Priority
- `Highest` - Critical severity vulnerabilities
- `High` - High severity vulnerabilities
- `Medium` - Medium severity vulnerabilities
- `Low` - Low severity vulnerabilities
- Map from the HIGHEST severity across all vulnerabilities in the PR

### Labels
- Array of strings, no spaces allowed in individual labels
- Standard labels: `["security", "dependabot", "automated"]`
- Labels help with JQL filtering: `labels = security AND labels = automated`

## Jira MCP Tools Reference

### create_issue
Creates a new Jira issue.
```
mcp__jira__create_issue(
  project_key: str,
  issue_type: str,      # "Bug"
  summary: str,
  description: str,     # Plain text
  priority: str,        # "Highest", "High", "Medium", "Low"
  labels: list[str]     # ["security", "dependabot", "automated"]
)
```

### get_issue
Retrieves an issue by key.
```
mcp__jira__get_issue(issue_key: str)  # e.g., "PROJ-123"
```

### update_issue
Updates fields on an existing issue.
```
mcp__jira__update_issue(
  issue_key: str,
  summary: str | None,
  description: str | None,
  priority: str | None,
  labels: list[str] | None
)
```

### search_issues
Search using JQL.
```
mcp__jira__search_issues(jql: str, max_results: int)
# Example: "project = SEC AND labels = security ORDER BY created DESC"
```

## Plain Text Formatting Tips

The Jira MCP accepts plain text and converts to Atlassian Document Format (ADF) internally.

### Tables
Use pipe-separated values:
```
| Header 1 | Header 2 |
|----------|----------|
| Value 1  | Value 2  |
```

### Lists
Use dashes or asterisks:
```
- Item 1
- Item 2
  - Sub-item
```

### Checkboxes
Use bracket syntax:
```
- [ ] Unchecked item
- [x] Checked item
```

### Links
Use plain URLs - they will be auto-linked:
```
https://github.com/org/repo/pull/123
```

### Bold/Emphasis
Not guaranteed in plain text conversion. Use CAPS or surrounding characters:
```
WARNING: Major version update
**Important** (may or may not render)
```
