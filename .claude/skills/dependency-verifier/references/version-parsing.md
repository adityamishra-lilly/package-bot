# Version Parsing from Lock Files

## Lock File Formats by Ecosystem

### Python (uv.lock)

TOML format with package tables:

```toml
[[package]]
name = "virtualenv"
version = "20.28.1"
source = { registry = "https://pypi.org/simple" }
```

**Parsing:**
```bash
grep -A5 'name = "virtualenv"' uv.lock | grep 'version = "' | sed 's/.*"\(.*\)".*/\1/'
```

### Python (poetry.lock)

TOML format:

```toml
[[package]]
name = "virtualenv"
version = "20.28.1"
```

**Parsing:**
```bash
grep -A3 'name = "virtualenv"' poetry.lock | grep 'version = "' | sed 's/.*"\(.*\)".*/\1/'
```

### Node.js (package-lock.json)

JSON format with nested structure:

```json
{
  "packages": {
    "node_modules/lodash": {
      "version": "4.17.21"
    }
  }
}
```

**Parsing:**
```bash
jq '.packages["node_modules/lodash"].version' package-lock.json
```

### Rust (Cargo.lock)

TOML format:

```toml
[[package]]
name = "serde"
version = "1.0.196"
```

**Parsing:**
```bash
grep -A2 'name = "serde"' Cargo.lock | grep 'version = "' | sed 's/.*"\(.*\)".*/\1/'
```

### Go (go.mod)

Plaintext module format:

```
require (
    golang.org/x/crypto v0.45.0
)
```

**Parsing:**
```bash
grep 'golang.org/x/crypto' go.mod | awk '{print $2}'
```

## Validation Patterns

### Version Format Regex

```regex
^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$
```

### Common Validation Checks

1. Version is not empty
2. Version matches expected format
3. Version satisfies minimum required version
4. No unexpected characters
