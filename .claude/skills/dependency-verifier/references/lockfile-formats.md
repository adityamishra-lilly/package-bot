# Lock File Formats Reference

## Overview

This reference documents the structure of lock files for different package managers.

## Python (uv) - uv.lock

Format: TOML

```toml
version = 1
requires-python = ">=3.11"

[[package]]
name = "virtualenv"
version = "20.28.1"
source = { registry = "https://pypi.org/simple" }
dependencies = [
    { name = "distlib" },
    { name = "filelock" },
    { name = "platformdirs" },
]
```

### Parsing
```bash
# Find package version
grep -A5 'name = "virtualenv"' uv.lock | grep 'version'
```

## Python (poetry) - poetry.lock

Format: TOML

```toml
[[package]]
name = "virtualenv"
version = "20.28.1"
description = "Virtual Python Environment builder"
optional = false
python-versions = ">=3.8"

[package.dependencies]
distlib = ">=0.3.7,<1"
filelock = ">=3.12.2,<4"
platformdirs = ">=3.9.1,<5"
```

### Parsing
```bash
# Find package version
grep -A3 'name = "virtualenv"' poetry.lock | grep 'version'
```

## Node.js (npm) - package-lock.json

Format: JSON

```json
{
  "name": "project",
  "lockfileVersion": 3,
  "packages": {
    "node_modules/lodash": {
      "version": "4.17.21",
      "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
      "integrity": "sha512-..."
    }
  }
}
```

### Parsing
```bash
# Find package version
jq '.packages["node_modules/lodash"].version' package-lock.json
```

## Node.js (yarn) - yarn.lock

Format: Custom (YAML-like)

```yaml
lodash@^4.17.0:
  version "4.17.21"
  resolved "https://registry.yarnpkg.com/lodash/-/lodash-4.17.21.tgz"
  integrity sha512-...
```

### Parsing
```bash
# Find package version
grep -A1 '^lodash@' yarn.lock | grep 'version'
```

## Rust (cargo) - Cargo.lock

Format: TOML

```toml
[[package]]
name = "serde"
version = "1.0.214"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "f55c3193aca71c12ad7890f1785d2b73e1b9f63a0bbc353c08ef26f68b3c2c5e"
dependencies = [
 "serde_derive",
]
```

### Parsing
```bash
# Find package version
grep -A2 'name = "serde"' Cargo.lock | grep 'version'
```

## Go - go.mod

Format: Go mod

```go
module example.com/myproject

go 1.21

require (
    golang.org/x/crypto v0.45.0
    github.com/containerd/containerd v1.7.29
)
```

### Parsing
```bash
# Find module version
grep 'golang.org/x/crypto' go.mod
```

## Go - go.sum

Format: Checksums

```
golang.org/x/crypto v0.45.0 h1:abc123...
golang.org/x/crypto v0.45.0/go.mod h1:def456...
```

### Parsing
```bash
# Find module checksum
grep 'golang.org/x/crypto v0.45.0' go.sum
```

## Validation Commands

| File | Validation Command |
|------|-------------------|
| uv.lock | `python -c "import tomllib; tomllib.load(open('uv.lock', 'rb'))"` |
| poetry.lock | `python -c "import tomllib; tomllib.load(open('poetry.lock', 'rb'))"` |
| package-lock.json | `jq . package-lock.json > /dev/null` |
| yarn.lock | Check for `@` patterns |
| Cargo.lock | `cargo metadata --format-version 1 > /dev/null` |
| go.mod | `go mod verify` |
| go.sum | Checksum format validation |
