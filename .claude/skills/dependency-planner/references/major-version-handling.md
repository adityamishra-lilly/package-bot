# Major Version Update Handling

## Overview

Major version updates require special handling due to potential breaking changes.

## Detecting Major Version Updates

### Semantic Versioning Rules

```
MAJOR.MINOR.PATCH

Major bump: 1.x.x -> 2.x.x (breaking changes)
Minor bump: 1.2.x -> 1.3.x (new features, backward compatible)
Patch bump: 1.2.3 -> 1.2.4 (bug fixes)
```

### Special Cases

1. **0.x to 1.x**: Always major (stability commitment)
2. **0.x.y to 0.x+1.z**: Potentially breaking (pre-1.0 convention)
3. **Pre-release versions**: -alpha, -beta, -rc may have breaking changes

## When Current Version is Null

If `current_version` is null in vulnerability data:

1. Use github-mcp to read the manifest file
2. Extract current version from:
   - `pyproject.toml`: `[project] version = "x.y.z"` or dependencies
   - `package.json`: `"dependencies": {"pkg": "^x.y.z"}`
   - `go.mod`: `require pkg v1.2.3`
   - `Cargo.toml`: `[dependencies] pkg = "x.y.z"`

## Choosing Fix Version

When multiple `fix_versions` are available:

```json
{
  "current_version": "1.6.0",
  "target_version": "2.2.0",
  "fix_versions": ["1.6.38", "1.7.27", "1.7.29", "2.0.4", "2.2.0"]
}
```

### Decision Tree

1. **Prefer same major version**: If 1.x fix available, use it
2. **Use highest patch in same minor**: 1.7.29 > 1.7.27
3. **Accept minor bump if no patch**: 1.6.0 -> 1.7.29
4. **Flag major bump**: Only if no minor/patch fix exists

### Example Selection

```
Current: 1.6.0
Available: [1.6.38, 1.7.27, 1.7.29, 2.0.4, 2.2.0]

Recommended: 1.7.29 (same major, fixes vulnerability)
Alternative: 1.6.38 (same minor, if 1.7.x breaks something)
Avoid: 2.x.x (major version, breaking changes likely)
```

## Documentation Requirements

When major version update is unavoidable:

```markdown
### [MAJOR_VERSION_UPDATE] Package: containerd (go)
- Current: 1.6.0 -> Target: 2.2.0
- Severity: high | CVSS: 7.3
- CVEs: CVE-2024-25621

**WARNING: Major version update - potential breaking changes**

#### Breaking Changes to Review:
- [ ] API changes in v2.0.0
- [ ] Configuration format changes
- [ ] Deprecated features removed

#### Changelog Links:
- https://github.com/containerd/containerd/releases/tag/v2.0.0

#### Alternative:
- Minor fix available: 1.7.29 (if compatible with other deps)
```

## Risk Assessment

| Scenario | Risk Level | Action |
|----------|-----------|--------|
| Patch only | Low | Auto-approve |
| Minor bump | Medium | Standard review |
| Major bump (fix available) | High | Use minor fix |
| Major bump (required) | Critical | Manual review |
