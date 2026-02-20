---
name: pull-request-reviewer
description: Evaluates PR fields and updates them directly via mcp__github__update_pull_request. Use when you need to validate and fix PR title, body, CVE references, and formatting in place.
allowed-tools: Read, Bash, Grep, Glob, WebFetch, TodoWrite
---

# Pull Request Reviewer

## Purpose

This skill evaluates the existing fields (title and body) of a pull request and
updates them directly via `mcp__github__update_pull_request` if they are incorrect
or incomplete. It does NOT leave comments, reviews, summaries, or recommendations.

## Core Workflow

```
1. FETCH   → mcp__github__get_pull_request owner repo pr_number
2. DIFF    → mcp__github__get_pull_request_diff owner repo pr_number
3. EVALUATE → Check title and body against criteria
4. UPDATE  → mcp__github__update_pull_request owner repo pr_number (if needed)
```

## Evaluation Criteria

### Title

The PR title must:
- Clearly indicate a security update
- Be descriptive and specific

**Correct:**
- `Security: Update vulnerable dependencies`
- `fix(deps): resolve CVE-2025-12345 in lodash`

**Incorrect (fix these):**
- `Update stuff`
- `fixes`
- `WIP`

### Body - Required Sections

The PR body must contain ALL of the following. If any are missing or malformed,
rebuild the body and update it.

#### 1. Vulnerability Table

```markdown
| Package | From | To | CVE | Severity |
|---------|------|-----|-----|----------|
| lodash | 4.17.0 | 4.17.21 | CVE-2025-12345 | high |
```

- All packages from the diff must be listed
- CVE/GHSA identifiers must be present for each
- Severity must be included (critical/high/medium/low)

#### 2. CVE/GHSA References

- Every advisory must be referenced: `CVE-YYYY-NNNNN` or `GHSA-xxxx-xxxx-xxxx`
- Cross-check against the actual diff to ensure none are missing

#### 3. Major Version Warnings (if applicable)

- Major version bumps (e.g. 1.x -> 2.x) must be flagged
- Include breaking change warnings

#### 4. Files Modified

- List all files changed in the PR
- Lock files are expected; source files are unexpected

#### 5. Formatting

- Tables must render correctly in markdown
- Links must be valid
- Co-Authored-By line must be present

## Update Rules

- Make at most ONE call to `mcp__github__update_pull_request` with all fixes combined
- If updating the body, include the ENTIRE corrected body (not a partial patch)
- If only the title needs fixing, update only the title
- If only the body needs fixing, update only the body
- If both need fixing, update both in one call
- If everything is correct, make NO update call

## What This Skill Does NOT Do

- Does NOT leave PR comments
- Does NOT submit PR reviews (approve/request changes)
- Does NOT output review reports or recommendations
- Does NOT modify code or files in the repository

## Ready-to-Use Scripts

| Script | Description |
|--------|-------------|
| [scripts/review-pr.sh](scripts/review-pr.sh) | Check PR fields |
| [scripts/check-diff.sh](scripts/check-diff.sh) | Validate PR diff |

## References

| Reference | When to Use |
|-----------|-------------|
| [references/review-criteria.md](references/review-criteria.md) | Field evaluation standards |
