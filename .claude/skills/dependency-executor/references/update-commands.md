# Update Commands Reference

## Overview

This reference contains all ecosystem-specific update commands for dependency remediation.

## Python

### uv (Recommended)
```bash
# Update single package
uv lock --upgrade-package <package>==<version>

# Update multiple packages
uv lock --upgrade-package pkg1==1.0.0 --upgrade-package pkg2==2.0.0
```

### poetry
```bash
# Update single package (lock only)
poetry update <package>@<version> --lock

# Update multiple packages
poetry update pkg1@1.0.0 pkg2@2.0.0 --lock
```

### pip (requirements.txt)
```bash
# Direct edit of requirements.txt
sed -i 's/package==.*/package==<version>/' requirements.txt

# Or use pip-tools
pip-compile --upgrade-package <package>==<version>
```

## Node.js

### npm
```bash
# Update without installing (lock only)
npm install <package>@<version> --package-lock-only

# Update multiple
npm install pkg1@1.0.0 pkg2@2.0.0 --package-lock-only
```

### yarn (v1)
```bash
# Update lock only
yarn add <package>@<version> --mode update-lockfile
```

### yarn (v2+/berry)
```bash
# Update lock only
yarn set resolution <package>@<version>
```

### pnpm
```bash
# Update lock only
pnpm update <package>@<version> --lockfile-only
```

## Rust

### cargo
```bash
# Update to specific version
cargo update -p <package>@<version>

# Update to latest compatible
cargo update -p <package>
```

## Go

### go mod
```bash
# Update to specific version (include 'v' prefix)
go get <module>@v<version>

# Clean up go.mod and go.sum
go mod tidy

# Example
go get golang.org/x/crypto@v0.45.0
go mod tidy
```

## Ruby

### bundler
```bash
# Update single gem
bundle update <gem> --conservative

# Update to specific version (edit Gemfile first)
bundle lock --update <gem>
```

## PHP

### composer
```bash
# Update single package
composer update <package>:<version> --lock

# Example
composer update vendor/package:1.2.3 --lock
```

## Version Specification

| Ecosystem | Exact Version | Range |
|-----------|--------------|-------|
| pip/uv | `==1.2.3` | `>=1.2.3` |
| poetry | `@1.2.3` | `^1.2.3` |
| npm/yarn/pnpm | `@1.2.3` | `^1.2.3` |
| cargo | `@1.2.3` | `1.2` |
| go | `@v1.2.3` | N/A |

## Lock-Only Flags

Critical for security updates - avoid installing packages:

| Manager | Lock-Only Flag |
|---------|---------------|
| npm | `--package-lock-only` |
| yarn | `--mode update-lockfile` |
| pnpm | `--lockfile-only` |
| poetry | `--lock` |
| uv | (default behavior) |
| cargo | (default behavior) |
| go | N/A (uses network) |

## Verification Commands

After update, verify version in lock file:

```bash
# Python (uv)
grep -A5 'name = "<package>"' uv.lock | grep version

# Python (poetry)
grep -A3 'name = "<package>"' poetry.lock | grep version

# npm
jq '.packages["node_modules/<package>"].version' package-lock.json

# Go
grep '<module>' go.mod
```
