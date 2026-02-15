"""FastMCP server instance."""

from fastmcp import FastMCP

from jira_mcp.lifespan import lifespan

mcp = FastMCP("jira-mcp", lifespan=lifespan)
