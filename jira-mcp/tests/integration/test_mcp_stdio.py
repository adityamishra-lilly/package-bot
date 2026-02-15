"""Integration test: spawn the MCP server subprocess and send initialize."""

from __future__ import annotations

import asyncio
import json
import sys

import pytest


@pytest.mark.asyncio
@pytest.mark.integration
async def test_server_responds_to_initialize():
    """Spawn jira-mcp as a subprocess and verify it handles MCP initialize."""
    env_vars = {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "fake-token",
    }

    import os

    env = {**os.environ, **env_vars}

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "jira_mcp",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    try:
        # Send MCP initialize request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1.0"},
            },
        }
        msg = json.dumps(request)
        proc.stdin.write(msg.encode() + b"\n")
        await proc.stdin.drain()

        # Read response with timeout
        try:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=10.0)
            response = json.loads(line)
            assert response.get("jsonrpc") == "2.0"
            assert response.get("id") == 1
            assert "result" in response
            result = response["result"]
            assert "serverInfo" in result
            assert result["serverInfo"]["name"] == "jira-mcp"
        except asyncio.TimeoutError:
            pytest.fail("Server did not respond within 10s")
    finally:
        proc.terminate()
        await proc.wait()
