"""Entry point for running the Jira MCP server: python -m jira_mcp"""

import jira_mcp.tools  # noqa: F401 — registers all tools with the server
from jira_mcp.server import mcp


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
