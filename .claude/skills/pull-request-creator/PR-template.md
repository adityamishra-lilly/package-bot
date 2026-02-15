# Dependency Security Remediation

**Repository**: {{REPOSITORY_NAME}}
**Organization**: {{ORG_NAME}}
**Branch**: {{REMEDIATION_BRANCH}}
**Date**: {{DATE}}
**Source**: {{ALERT_SOURCE}}
**Automated By**: {{AGENT_NAME}}

---

## Executive Summary

This pull request remediates one or more **security vulnerabilities in project dependencies**
identified via automated security alerts.

The changes are **minimal and targeted**, updating only the affected dependencies to
explicitly recommended secure versions.

### Risk Summary

| Severity | Count |
|---------|-------|
| Critical | {{CRITICAL_COUNT}} |
| High | {{HIGH_COUNT}} |
| Medium | {{MEDIUM_COUNT}} |
| Low | {{LOW_COUNT}} |

**Overall Risk Addressed**: {{OVERALL_RISK_LEVEL}}

---

## Affected Dependencies

| Ecosystem | Package | Before | After | Manifest |
|----------|--------|--------|-------|----------|
{{DEPENDENCY_TABLE}}

---

## Security Advisories Addressed

{{#each ADVISORIES}}
### {{PACKAGE_NAME}}

- **Severity**: {{SEVERITY}}
- **CVEs**: {{CVES}}
- **GHSAs**: {{GHSAS}}
- **Vulnerable Range**: {{VULNERABLE_RANGE}}
- **Fixed Version**: {{FIX_VERSION}}
- **Reference**: {{REFERENCE_URL}}

{{/each}}

---

## Changes Made

- Updated dependency lock files to secure versions
- No application code changes
- No dependency installs performed
- No formatting-only changes

### Files Modified

```text
{{MODIFIED_FILES}}