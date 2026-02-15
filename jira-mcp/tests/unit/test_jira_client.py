"""Tests for JiraClient using respx to mock httpx."""

import pytest
import respx
from httpx import Response

from jira_mcp.jira.client import JiraClient
from jira_mcp.jira.errors import (
    JiraAuthenticationError,
    JiraNotFoundError,
    JiraValidationError,
)

BASE_URL = "https://test.atlassian.net"
API_BASE = f"{BASE_URL}/rest/api/3"


@pytest.fixture
async def client():
    c = JiraClient(base_url=BASE_URL, email="test@example.com", api_token="tok")
    yield c
    await c.close()


@respx.mock
@pytest.mark.asyncio
async def test_get_issue(client):
    route = respx.get(f"{API_BASE}/issue/PROJ-1").mock(
        return_value=Response(200, json={"key": "PROJ-1", "fields": {"summary": "Test"}})
    )
    result = await client.get_issue("PROJ-1")
    assert result["key"] == "PROJ-1"
    assert route.called


@respx.mock
@pytest.mark.asyncio
async def test_create_issue(client):
    respx.post(f"{API_BASE}/issue").mock(
        return_value=Response(201, json={"id": "1", "key": "PROJ-2", "self": "..."})
    )
    result = await client.create_issue({"summary": "New", "project": {"key": "PROJ"}})
    assert result["key"] == "PROJ-2"


@respx.mock
@pytest.mark.asyncio
async def test_update_issue(client):
    respx.put(f"{API_BASE}/issue/PROJ-1").mock(return_value=Response(204))
    await client.update_issue("PROJ-1", {"summary": "Updated"})


@respx.mock
@pytest.mark.asyncio
async def test_delete_issue(client):
    respx.delete(f"{API_BASE}/issue/PROJ-1").mock(return_value=Response(204))
    await client.delete_issue("PROJ-1")


@respx.mock
@pytest.mark.asyncio
async def test_search_issues(client):
    respx.post(f"{API_BASE}/search").mock(
        return_value=Response(200, json={"total": 1, "issues": [{"key": "PROJ-1"}]})
    )
    result = await client.search_issues("project = PROJ")
    assert result["total"] == 1


@respx.mock
@pytest.mark.asyncio
async def test_add_comment(client):
    respx.post(f"{API_BASE}/issue/PROJ-1/comment").mock(
        return_value=Response(201, json={"id": "10"})
    )
    result = await client.add_comment("PROJ-1", {"type": "doc", "version": 1, "content": []})
    assert result["id"] == "10"


@respx.mock
@pytest.mark.asyncio
async def test_get_transitions(client):
    respx.get(f"{API_BASE}/issue/PROJ-1/transitions").mock(
        return_value=Response(200, json={"transitions": [{"id": "1", "name": "Done"}]})
    )
    result = await client.get_transitions("PROJ-1")
    assert len(result["transitions"]) == 1


@respx.mock
@pytest.mark.asyncio
async def test_list_projects(client):
    respx.get(f"{API_BASE}/project").mock(
        return_value=Response(200, json=[{"key": "PROJ", "name": "Project"}])
    )
    result = await client.list_projects()
    assert result[0]["key"] == "PROJ"


@respx.mock
@pytest.mark.asyncio
async def test_auth_error(client):
    respx.get(f"{API_BASE}/issue/PROJ-1").mock(
        return_value=Response(401, text="Unauthorized")
    )
    with pytest.raises(JiraAuthenticationError):
        await client.get_issue("PROJ-1")


@respx.mock
@pytest.mark.asyncio
async def test_not_found_error(client):
    respx.get(f"{API_BASE}/issue/PROJ-999").mock(
        return_value=Response(404, text="Not Found")
    )
    with pytest.raises(JiraNotFoundError):
        await client.get_issue("PROJ-999")


@respx.mock
@pytest.mark.asyncio
async def test_validation_error(client):
    respx.post(f"{API_BASE}/issue").mock(
        return_value=Response(400, text="Bad Request")
    )
    with pytest.raises(JiraValidationError):
        await client.create_issue({})
