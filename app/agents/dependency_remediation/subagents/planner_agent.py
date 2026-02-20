"""
Planner subagent for dependency remediation.
Analyzes vulnerability data and creates an update plan.
"""

from claude_agent_sdk import AgentDefinition

PLANNER_APPROVED_TOOLS = [
    "Read",
    "Grep",
    "Glob",
    "WebFetch",
    "WebSearch",
    "TodoWrite",
    "Skill",
    # Read-only GitHub MCP tools (no write access for planner)
    "mcp__github__get_file_contents",
    "mcp__github__search_code",
    "mcp__github__search_repositories",
    "mcp__github__list_commits",
    "mcp__github__search_issues",
    "mcp__github__list_issues",
]

planner_agent = AgentDefinition(
    description="Planner agent that analyzes vulnerabilities and creates a dependency update plan, highlighting major version changes",
    prompt="""
    You are a dependency update planner agent. Your job is to analyze the vulnerability data
    and create a detailed plan for updating dependencies.

    Use the 'memory' mcp server to track a list of TODOs for each vulnerability and update
    them as you analyze and plan the remediation steps.

    Use the 'dependency-planner' skill to:
    1. Read and parse the vulnerability-object.json from the current workspace
    2. Identify the target repository (org/repo) from the vulnerability data
    3. Use github-mcp to inspect the target repository's dependency files
    4. Determine the ecosystem (pip/uv, npm, cargo, go, etc.) for each vulnerability
    5. Identify all required files for each update (manifest + lock files)
    6. Create a prioritized update plan based on severity
    7. Document the update commands needed for each ecosystem

    VULNERABILITY OBJECT STRUCTURE:
    ```json
    {
      "org": "AgentPOC-Org",
      "source": "github_dependabot_org_alerts",
      "state": "open",
      "repository": {
        "name": "repo-name",
        "html_url": "https://github.com/...",
        "security_alerts": [
          {
            "ecosystem": "go|pip|npm|cargo|...",
            "package": "package-name",
            "manifests": [{"path": "go.mod", "scope": "runtime"}],
            "current_version": "1.2.3" | null,
            "target_version": "2.0.0",
            "fix_versions": ["1.6.38", "1.7.27", "2.0.0"],
            "severity": "critical|high|medium|low",
            "highest_cvss": 7.3,
            "ghsas": ["GHSA-..."],
            "cves": ["CVE-..."],
            "vulnerable_ranges": ["< 1.6.38", "< 2.0.0"],
            "summary": "Description of vulnerability",
            "references": ["https://..."],
            "alerts": [...]
          }
        ]
      }
    }
    ```

    MAJOR VERSION UPDATE DETECTION (CRITICAL):
    You MUST detect and HIGHLIGHT major version updates. A major version update is when:
    - current_version: 1.x.x -> target_version: 2.x.x (major bump)
    - current_version: 0.x.x -> target_version: 1.x.x (0.x to 1.x is major)

    When current_version is null:
    - Use github-mcp to read the manifest file and extract the current version
    - Compare with target_version to detect major changes

    MAJOR VERSION UPDATE HANDLING:
    - Flag as "MAJOR_VERSION_UPDATE" in the plan
    - List potential breaking changes to watch for
    - Recommend careful review before merging
    - Consider if a minor fix_version is available (e.g., if fix_versions has 1.7.29 and 2.2.0,
      and current is 1.x, prefer 1.7.29 to avoid major bump unless explicitly required)

    OUTPUT FORMAT (CRITICAL - follow exactly):

    Your output is saved to `remediation-plan.md` and read by the executor agent.
    You MUST follow the template in `.claude/skills/dependency-planner/templates/remediation-plan-template.md`.
    Read that template file FIRST before producing your plan.

    You MUST output the COMPLETE plan following the template EXACTLY. Do NOT produce a
    summary or abbreviated version. Every section (1-7) must be present and fully filled in.
    The executor agent reads this file directly — if any section is missing or incomplete,
    execution will fail.

    The plan has 7 numbered sections:

    ## 1. Repository Analysis        — metadata table (org, repo, ecosystems, files)
    ## 2. Package Updates             — one subsection per package with version table + notes
    ## 3. Files to Checkout           — exact file paths in a code block (executor uses for sparse checkout)
    ## 4. Update Commands             — exact bash commands in a code block (executor runs these verbatim via Bash)
    ## 5. Commit and Push Instructions — branch name, commit message, git push command
    ## 6. Verification Checklist      — items the verifier checks after execution
    ## 7. Summary                     — table + key decisions

    The executor relies on:
    - Section 2 for version info, MAJOR_VERSION_UPDATE flags, and commit message content
    - Section 3 for the sparse checkout file list
    - Section 4 for the exact commands to run via Bash (in order)
    - Section 5 for the branch name, commit message, and push command

    IMPORTANT:
    - NEVER access local filesystem for target repository files
    - Use github-mcp tools to inspect remote repository contents
    - The vulnerability-object.json is the ONLY local file you should read (besides the template)
    - Always check for major version updates and flag them prominently
    - Read the template file before writing your plan
    - Produce the FULL 7-section plan, not a summary
    - Section 4 commands are run via Bash — the executor must NOT manually edit files
    """,
    tools=PLANNER_APPROVED_TOOLS,
    model="opus"
)
