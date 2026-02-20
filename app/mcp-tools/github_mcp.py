import os
from typing import Dict, Any


def get_github_mcp_config() -> Dict[str, Any]:
    """
    Build GitHub MCP server configuration for Claude Agent SDK.
    
    Uses GIT_COMMAND_TOKEN from environment for authentication.
    
    Returns:
        MCP server configuration dict for stdio transport
        
    Raises:
        ValueError: If GIT_COMMAND_TOKEN is not set
    """
    github_token = os.getenv("GIT_COMMAND_TOKEN")
    if not github_token:
        raise ValueError("GIT_COMMAND_TOKEN environment variable is required for GitHub MCP")
    
    # GitHub MCP server configuration (stdio transport)
    # See: https://github.com/github/github-mcp-server
    return {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-github"
        ],
        "env": {
            "GITHUB_PERSONAL_ACCESS_TOKEN": github_token
        }
    }


def get_github_mcp_tools() -> list[str]:
    """
    Get list of GitHub MCP tool names for allowlist based on agent type.
    
    Args:
        agent_type: Type of agent ("planner" or "executor")
        
    Returns:
        List of tool names prefixed with 'mcp__github__'
    """
    # GitHub MCP server provides these tools:
    # - create_or_update_file
    # - search_repositories
    # - create_repository
    # - get_file_contents
    # - push_files
    # - create_issue
    # - create_pull_request
    # - update_pull_request
    # - get_pull_request
    # - get_pull_request_diff
    # - fork_repository
    # - create_branch
    # - search_code
    # - search_issues
    # - list_commits
    # - list_issues

    return [
            "mcp__github__create_branch",
            "mcp__github__create_or_update_file",
            "mcp__github__push_files",
            "mcp__github__create_pull_request",
            "mcp__github__update_pull_request",
            "mcp__github__get_pull_request",
            "mcp__github__get_pull_request_diff",
            "mcp__github__get_file_contents",
            "mcp__github__search_code",
            "mcp__github__search_repositories",
            "mcp__github__list_commits"
          ]
