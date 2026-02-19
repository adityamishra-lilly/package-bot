# Remediation Plan Template

The planner agent MUST output its plan in EXACTLY this format.
The executor agent reads this plan from `remediation-plan.md` in the workspace directory.

Both agents rely on the section headers and structure below. Do NOT rename sections,
reorder them, or omit required fields.

---

<!-- TEMPLATE START — planner: fill in all {placeholders}, remove HTML comments -->

## 1. Repository Analysis

| Field | Value |
|-------|-------|
| Organization | {org} |
| Repository | {repo_name} |
| Repository URL | {html_url} |
| Ecosystems | {comma-separated list, e.g. go, pip} |
| Manifest files | {comma-separated, e.g. go.mod, pyproject.toml} |
| Lock files | {comma-separated, e.g. go.sum, uv.lock} |
| Total vulnerabilities | {N} |
| Highest severity | {critical/high/medium/low} |

## 2. Package Updates

<!-- Repeat this subsection for EACH package, ordered by severity (critical first) -->

### 2.{n}. {package_name} ({ecosystem})

| Field | Value |
|-------|-------|
| Current version | {current_version or "unknown"} |
| Recommended version | {version the executor should install} |
| Dependabot target | {target_version from vulnerability object} |
| Update type | {MAJOR / MINOR / PATCH} |
| Severity | {severity} |
| CVSS | {highest_cvss} |
| CVEs | {comma-separated CVE list} |
| GHSAs | {comma-separated GHSA list} |
| Scope | {runtime / development / indirect} |

<!-- For MAJOR updates, include the following block -->
**[MAJOR_VERSION_UPDATE]**
- Breaking changes: {description of potential breaking changes}
- Alternative fix versions: {list of minor/patch alternatives if available, or "none"}
- Recommendation: {e.g. "Use v1.7.29 instead to avoid module path change" or "Proceed — no minor fix available"}
- Rationale: {why this recommendation}

<!-- For non-major updates -->
**Notes:** {any relevant context, or "Straightforward update, no breaking changes expected."}

## 3. Files to Checkout

<!-- Exact file paths for sparse checkout, one per line -->

```
{file_path_1}
{file_path_2}
```

## 4. Update Commands

<!-- Exact bash commands the executor must run, in order -->
<!-- Include comments explaining each step -->

```bash
# Step 1: {description}
{command}

# Step 2: {description}
{command}

# Final: Clean up / tidy
{tidy_command}
```

**Command notes:**
- {Any important notes about command order, dependencies, or platform quirks}

## 5. Verification Checklist

<!-- The verifier agent uses this checklist after execution -->

- [ ] {manifest_file} contains {package} at version {recommended_version}
- [ ] {lock_file} has been updated with new checksums
- [ ] No unintended dependency changes introduced
- [ ] Build/compilation succeeds (`{build_command}`)
- [ ] All CVEs resolved: {CVE-1} (fixed in >= {version}), {CVE-2} (fixed in >= {version})

## 6. Summary

| Package | Current | Recommended | Major? | Severity | CVE Count |
|---------|---------|-------------|--------|----------|-----------|
| {pkg1} | {curr} | {rec} | {Yes/No} | {sev} | {n} |
| {pkg2} | {curr} | {rec} | {Yes/No} | {sev} | {n} |

**Key decisions:**
- {Bullet point summarizing any important decisions, e.g. version downgrades to avoid major bumps}

<!-- TEMPLATE END -->
