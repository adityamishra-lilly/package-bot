#!/usr/bin/env python3
"""Validate Jira MCP configuration and test connectivity."""

import asyncio
import sys

from jira_mcp.jira.client import JiraClient
from jira_mcp.settings import JiraSettings


async def main() -> int:
    print("Loading settings...")
    try:
        settings = JiraSettings()
    except Exception as e:
        print(f"FAIL: Could not load settings: {e}")
        print("Ensure JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN are set.")
        return 1

    print(f"  JIRA_URL: {settings.url}")
    print(f"  JIRA_EMAIL: {settings.email}")
    print(f"  JIRA_API_TOKEN: {'*' * 8}...{settings.api_token[-4:]}")

    print("\nTesting connectivity...")
    client = JiraClient(
        base_url=settings.url,
        email=settings.email,
        api_token=settings.api_token,
        timeout=settings.timeout,
    )

    try:
        projects = await client.list_projects()
        print(f"  OK: Found {len(projects)} accessible projects")
        for p in projects[:5]:
            print(f"    - {p.get('key')}: {p.get('name')}")
        if len(projects) > 5:
            print(f"    ... and {len(projects) - 5} more")
        return 0
    except Exception as e:
        print(f"  FAIL: {e}")
        return 1
    finally:
        await client.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
