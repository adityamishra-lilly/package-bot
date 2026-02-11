# Package Update Executor Skill

This skill consumes a **Dependabot-compatible JSON alert payload** and performs
**minimal, deterministic dependency upgrades** while avoiding unnecessary file
checkouts, installs, or formatting changes.

---

## ⚠️ CRITICAL: Repository Context

**The vulnerability payload describes a REMOTE repository, NOT the local working directory.**

### Orchestration Context

This skill is executed by a Temporal activity (`execute_agent_activity`) that:
1. Creates a dedicated workspace directory: `workspace/{repo}_{timestamp}/`
2. Generates `vulnerability-object.json` containing the target repository's alert data
3. Sets the working directory to this workspace before invoking the agent
4. The agent's current working directory IS the workspace containing `vulnerability-object.json`

### Before ANY file operations:

1. **Parse `vulnerability-object.json` completely** from the current working directory (the workspace)
2. **Extract the target repository identity:**
   - `org` → GitHub organization (e.g., `AgentPOC-Org`)
   - `repository.name` → Target repository name (e.g., `python-uv-test`)
   - `repository.html_url` → Full GitHub URL
3. **Use github-mcp tools for ALL file access** to the target repository
4. **NEVER search the local filesystem** for target repository files
5. The workspace directory contains:
   - `vulnerability-object.json` (provided by orchestrator)
   - Temporary clone subdirectory (created during remediation)

### ❌ Common Mistakes to Avoid

DO NOT:
- Search local filesystem with `ls`, `find`, `cat`, or `grep` for dependency files
- Read local `poetry.lock`, `package-lock.json`, `uv.lock`, etc. from the orchestration directory
- Assume the vulnerability is in the current working directory
- Use local file tools before parsing the vulnerability object

### ✅ Correct Approach

DO:
- Read `vulnerability-object.json` first
- Use `github-mcp get_file_contents` to access target repository files
- Verify you're working with `{org}/{repository.name}` from the JSON, not the local directory
- Create a sparse clone in a new subdirectory separate from the orchestration directory

---

## Supported Ecosystems

| Ecosystem | Primary Manifest | Lock / Resolution Files |
|----------|-----------------|--------------------------|
| pip (uv) | `pyproject.toml` | `uv.lock` |
| pip (poetry) | `pyproject.toml` | `poetry.lock` |
| npm | `package.json` | `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml` |
| cargo | `Cargo.toml` | `Cargo.lock` |
| others | inferred via github-mcp search |

---

## Prerequisites

- github-mcp access with:
  - clone
  - branch creation
  - commit
  - pull request creation
- Tooling available in execution environment:
  - `git`
  - ecosystem-specific package manager (`uv`, `poetry`, `npm`, `cargo`, etc.)
- Network access for dependency resolution (no install required)

---

## High-Level Workflow

0. **Validate Repository Context** ⚠️
1. **Parse Alert Payload**
2. **Determine Required Files**
3. **Minimal Sparse Clone**
4. **Validate File Presence**
5. **Upgrade Vulnerable Dependencies**
6. **Commit Changes**
7. **Create Pull Request**

---

## Step 0: Validate Repository Context ⚠️

**PURPOSE: Ensure you're working with the correct remote repository, not local files**

### Orchestration Flow

The `execute_agent_activity` (Temporal activity) has:
1. Created a workspace directory for this specific repository
2. Generated `vulnerability-object.json` containing alert data for ONE repository
3. Set your working directory to this workspace
4. Invoked the agent (you) to process this single repository

### Required Actions

1. **Read `vulnerability-object.json`** from the current working directory (the workspace)
2. **Extract and store:**
   ```json
   {
     "org": "AgentPOC-Org",
     "source": "github_dependabot_org_alerts",
     "state": "open",
     "repository": {
       "name": "python-uv-test",
       "html_url": "https://github.com/AgentPOC-Org/python-uv-test",
       "security_alerts": [...]
     }
   }
   ```
3. **Verify you understand the target:**
   - Target repository: `{org}/{repository.name}`
   - This is a REMOTE repository accessed via github-mcp
   - Your workspace directory only contains the vulnerability JSON, not the target repository

### Anti-Patterns (DO NOT DO THIS)

❌ **WRONG - Searching local filesystem:**
```bash
# DO NOT DO THIS
find . -name "uv.lock"
ls poetry.lock
cat package-lock.json
grep "virtualenv" poetry.lock
```

❌ **WRONG - Reading local dependency files:**
```bash
# DO NOT DO THIS
read_file poetry.lock
read_file package-lock.json
search_files "." "virtualenv"
```

### Correct Pattern (DO THIS)

✅ **RIGHT - Read vulnerability object from workspace:**
```bash
# Step 1: Read the vulnerability payload (in current workspace directory)
read_file vulnerability-object.json
```

✅ **RIGHT - Then use github-mcp for remote files:**
```bash
# Step 2: Access target repository files via github-mcp
# Use {org}/{repo-name} extracted from vulnerability-object.json
github-mcp get_file_contents {org}/{repo-name}/uv.lock
github-mcp get_file_contents {org}/{repo-name}/pyproject.toml
```

### Architecture Context

```
RemediationOrchestratorWorkflow (Temporal)
  └─ For each repository in remediation plan:
       └─ execute_agent_activity
            ├─ Creates workspace/{repo}_{timestamp}/
            ├─ Generates vulnerability-object.json
            ├─ Sets cwd to workspace
            └─ Invokes run_remediation_agent
                 └─ YOU (package-update-executor skill)
                      ├─ Read vulnerability-object.json
                      ├─ Use github-mcp for remote access
                      ├─ Create sparse clone in subdirectory
                      └─ Create PR
```

---

## Step 1: Parse Vulnerability Data

**Note:** This step assumes you've already completed Step 0 and have the repository context.

The `vulnerability-object.json` file in your current workspace was generated by the orchestrator and contains:

### Data Structure
```json
{
  "org": "AgentPOC-Org",
  "source": "github_dependabot_org_alerts",
  "state": "open",
  "repository": {
    "name": "python-uv-test",
    "html_url": "https://github.com/...",
    "security_alerts": [
      {
        "ecosystem": "pip",
        "package": "virtualenv",
        "manifests": [{"path": "uv.lock"}],
        "target_version": "20.28.1",
        "fix_versions": ["20.28.1"],
        "severity": "moderate",
        "ghsas": ["GHSA-..."],
        "cves": ["CVE-2025-..."]
      }
    ]
  }
}
```

### Extract Required Information

From `vulnerability-object.json`:
- `org` (GitHub organization)
- `repository.name` (target repository name)
- `repository.html_url` (repository URL)
- For each item in `repository.security_alerts[]`:
  - `ecosystem`
  - `package`
  - `manifests[].path`
  - `target_version`
  - `fix_versions[]`
  - `severity`, `ghsas`, `cves` (for PR documentation)

### Rules
- Prefer the **highest safe version** from `fix_versions`
- Do **not** infer versions not explicitly listed
- Store the full repository identifier: `{org}/{repository.name}`
- This data represents a single repository (not multiple repos)

---

## Step 2: Determine Minimal Required Files

### Access Pattern ⚠️

Use **github-mcp** to:
1. Verify manifest files exist in the **target repository** (use `{org}/{repository.name}` from Step 0)
2. Read companion files to understand the package manager setup
3. Identify all required files for the ecosystem

### Primary Rule

The agent must clone **only**:
- Files explicitly listed in `manifests[].path`
- Any **minimum required companion files** needed by the ecosystem

### Examples

#### Python (uv)
If manifest path includes:
- `uv.lock`

Then required files are:
- `uv.lock`
- `pyproject.toml` (required by `uv lock`)

**Access via github-mcp:**
```
github-mcp get_file_contents {org}/{repo-name}/uv.lock
github-mcp get_file_contents {org}/{repo-name}/pyproject.toml
```

#### Node.js
If manifest path includes:
- `package-lock.json`

Then required files are:
- `package.json`
- `package-lock.json`

**Access via github-mcp:**
```
github-mcp get_file_contents {org}/{repo-name}/package.json
github-mcp get_file_contents {org}/{repo-name}/package-lock.json
```

#### Cargo
If manifest path includes:
- `Cargo.lock`

Then required files are:
- `Cargo.toml`
- `Cargo.lock`

**Access via github-mcp:**
```
github-mcp get_file_contents {org}/{repo-name}/Cargo.toml
github-mcp get_file_contents {org}/{repo-name}/Cargo.lock
```

### Discovery

If required companion files are not explicitly known:
- Use **github-mcp search** or **list_files** on the target repository
- Do not clone the full repository
- Do not search the local filesystem

### Anti-Patterns (DO NOT DO)

❌ Reading local files instead of remote:
```bash
grep "dependencies" poetry.lock  # WRONG - local file
cat package.json                  # WRONG - local file
```

❌ Searching local filesystem:
```bash
find . -name "*.toml"            # WRONG - local search
ls -la                           # WRONG - local directory
```

### Correct Patterns (DO THIS)

✅ Use github-mcp for remote repository access:
```
github-mcp get_file_contents AgentPOC-Org/python-uv-test/pyproject.toml
github-mcp list_files AgentPOC-Org/python-uv-test
```

✅ Verify repository identity matches vulnerability object:
```
Target: {org}/{repository.name} from vulnerability-object.json
NOT: current working directory
```

---

## Step 3: Minimal Sparse Clone

Create a sparse clone in a **new subdirectory** within your current workspace, Please follow and execute the steps carefully.

### Approach: Sparse Checkout with Windows Compatibility

```bash
# Create a subdirectory for the clone within the workspace
# (You are already in workspace/{repo}_{timestamp}/)
mkdir -p clone
cd clone

# Clone the TARGET repository (from vulnerability-object.json)
git clone --no-checkout --filter=blob:none $repo_url repo
cd repo

# Create a fix branch
git checkout -b fix/security-alerts-$(date +%Y%m%d-%H%M%S)

# Configure sparse checkout with --no-cone mode (cross-platform compatible)
git sparse-checkout init --no-cone

# Set required files using forward slashes (/) even on Windows
# Example: git sparse-checkout set pyproject.toml uv.lock
git sparse-checkout set <required_file_paths...>

# Checkout the files Execute this EXACT command
git checkout
```

### Windows Path Compatibility

- **Always use forward slashes** (`/`) in sparse-checkout paths, even on Windows
- Example: `src/main.py` not `src\main.py`
- Use `--no-cone` mode for better cross-platform compatibility

# Create fix branch
git checkout -b fix/security-alerts-$(date +%Y%m%d-%H%M%S)


# Verify required files are present
ls -la
```

**Important:**
- `<repo_url>` comes from `repository.html_url` in the vulnerability object
- The clone is created in a NEW directory, not the current working directory
- All subsequent git operations happen in this cloned workspace
- If sparse checkout fails, use the fallback approach to ensure MINIMAL files only
- Delete ALL unnecessary files after clone to avoid full repository checkout

---

## Step 4: Validate File Presence

After sparse checkout, verify ALL required files exist:

```bash
test -f <file> || exit 1
```

Rules:
- If files are missing:
    - Abort remediation
    - Record failure reason in logs
    - Do not attempt dependency updates
- Files must be present in the CLONED repository workspace, not the orchestration directory

---

## Step 5: Upgrade Vulnerable Dependencies

For each vulnerable package:
- Use ecosystem-specific commands to upgrade to the target version
- Run commands in the CLONED repository workspace

### Python (uv)
```bash
uv lock --upgrade-package <package>==<target_version>
```

### Python (poetry)
```bash
poetry update <package>@<target_version> --lock
```

### Node.js
```bash
npm install <package>@<target_version> --package-lock-only
```

### Cargo
```bash
cargo update -p <package>:<target_version>
```

Rules:
- Do not perform a full upgrade or install
- Only modify files necessary to update the vulnerable package
- Avoid changes to unrelated dependencies or formatting
- All commands run in the cloned workspace, not the orchestration directory

---

## Step 6: Commit Minimal Changes

```bash
git add <required_file_paths...>
git commit -m "chore(deps): fix security alerts for <packages>"
```

Changes are committed in the cloned workspace repository.

---

## Step 7: Create Pull Request

### ⚠️ CRITICAL: PR Body Formatting

**The PR body MUST use actual newlines, NOT escaped `\n` characters.**

This is the #1 most common formatting error. When calling `mcp__github__create_pull_request`, the `body` parameter must be a **multi-line string with real line breaks**.

#### ❌ WRONG - Using \n escape sequences:
```json
{
  "body": "## Security Remediation\n\nThis PR upgrades 2 transitive dependencies...\n\n## Vulnerabilities Fixed\n\n### filelock"
}
```

This will render as literal `\n` text in GitHub, breaking all markdown formatting.

#### ✅ RIGHT - Using actual newlines:
```json
{
  "body": "## Security Remediation

This PR upgrades 2 transitive dependencies...

## Vulnerabilities Fixed

### filelock"
}
```

**Rule:** Each line of the PR body should be a separate line in your JSON string, not `\n\n` or other escape sequences.

---

READ [../references/PR-template.md](../references/PR-template.md) for the pull request template.

Use github-mcp to create a pull request with the committed changes, targeting the default branch.

### Correct Format Example

```
mcp__github__create_pull_request with arguments:
{
  "owner": "AgentPOC-Org",
  "repo": "python-uv-test",
  "title": "Security: Update filelock and virtualenv",
  "body": "# Security Remediation — Dependency Upgrade

This PR upgrades vulnerable transitive dependencies to resolve 3 Dependabot alerts.

## Vulnerabilities Resolved

| Package | Previous | Patched | CVE(s) |
|---------|----------|---------|--------|
| filelock | 3.18.0 | 3.20.3 | CVE-2025-68146 |

## Changes
- File modified: uv.lock
- Method: uv lock --upgrade-package filelock>=3.20.3

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>",
  "head": "fix/security-alerts-20260208",
  "base": "main"
}
```

### PR Body Construction Rules

1. **Use actual newlines** - Each line should be a separate line in the string, not `\n`
2. **Markdown formatting** - Use proper markdown headers (`#`, `##`), tables, and lists
3. **Co-Authored-By format** - Use `Name <email>` format (with angle brackets)
4. **Include vulnerability details**:
   - Package names and versions
   - CVE/GHSA identifiers
   - Severity levels
   - Fix versions
5. **Document changes made**:
   - Files modified
   - Commands used
   - No functional changes disclaimer

### Common Mistakes to Avoid

❌ **WRONG - Using escaped newlines:**
```json
{
  "body": "# Title\n\nThis is wrong\n\n## Section"
}
```

This renders as: `# Title\n\nThis is wrong\n\n## Section` (literal backslash-n characters visible in GitHub)

❌ **WRONG - Malformed Co-Authored-By:**
```
Co-Authored-By: Claude noreply@anthropic.com
```

✅ **RIGHT - Actual newlines and proper format:**
```json
{
  "body": "# Title

This is correct

## Section

Co-Authored-By: Claude <noreply@anthropic.com>"
}
```

This renders as proper markdown with line breaks and formatted headers.

### PR Metadata Rules

- **Title**: Clear, concise, mentions the security fix and affected packages
- **Source branch**: The fix branch created in Step 3 (e.g., `fix/security-alerts-20260208`)
- **Target branch**: Typically `main` or the default branch
- **Owner/Repo**: From `{org}/{repository.name}` in vulnerability-object.json

---

## Summary: Key Corrections

| Issue | Solution |
|-------|----------|
| Searching local filesystem | Use github-mcp for all target repository access |
| Reading local dependency files | Read from `{org}/{repository.name}` via github-mcp |
| Confusing local vs remote repos | Always parse vulnerability-object.json first (Step 0) |
| Working in wrong directory | Create separate workspace for sparse clone |
| Incorrect file paths | Use paths from `manifests[].path` in vulnerability object |