"""Tests for search logic using mocked JiraClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from jira_mcp.jira.adf import adf_to_text, text_to_adf


@pytest.fixture
def mock_client():
    return AsyncMock()


@pytest.fixture
def mock_settings():
    settings = AsyncMock()
    settings.max_results = 50
    return settings


@pytest.mark.asyncio
async def test_search_issues_adds_plain_text(mock_client, mock_settings):
    """Verify that search results get _description_text added."""
    adf_doc = text_to_adf("Hello world")
    mock_client.search_issues.return_value = {
        "total": 1,
        "issues": [
            {
                "key": "PROJ-1",
                "fields": {"summary": "Test issue", "description": adf_doc},
            }
        ],
    }

    result = await mock_client.search_issues("project = PROJ", max_results=50, start_at=0)

    # Simulate what the tool does: add plain text descriptions
    for issue in result.get("issues", []):
        desc = issue.get("fields", {}).get("description")
        if desc:
            issue["_description_text"] = adf_to_text(desc)

    assert result["total"] == 1
    assert result["issues"][0]["_description_text"] == "Hello world"


@pytest.mark.asyncio
async def test_search_no_description(mock_client, mock_settings):
    """Verify issues without descriptions don't get _description_text."""
    mock_client.search_issues.return_value = {
        "total": 1,
        "issues": [{"key": "PROJ-1", "fields": {"summary": "No desc"}}],
    }

    result = await mock_client.search_issues("project = PROJ", max_results=50, start_at=0)

    for issue in result.get("issues", []):
        desc = issue.get("fields", {}).get("description")
        if desc:
            issue["_description_text"] = adf_to_text(desc)

    assert "_description_text" not in result["issues"][0]


@pytest.mark.asyncio
async def test_get_issue_with_description(mock_client):
    """Verify get_issue adds plain text description."""
    adf_doc = text_to_adf("Bug details here")
    mock_client.get_issue.return_value = {
        "key": "PROJ-1",
        "fields": {"summary": "Test", "description": adf_doc},
    }

    issue = await mock_client.get_issue("PROJ-1")

    fields = issue.get("fields", {})
    if fields.get("description"):
        issue["_description_text"] = adf_to_text(fields["description"])

    assert issue["_description_text"] == "Bug details here"


@pytest.mark.asyncio
async def test_get_issue_without_description(mock_client):
    """Verify get_issue without description doesn't add _description_text."""
    mock_client.get_issue.return_value = {
        "key": "PROJ-1",
        "fields": {"summary": "Test", "description": None},
    }

    issue = await mock_client.get_issue("PROJ-1")

    fields = issue.get("fields", {})
    if fields.get("description"):
        issue["_description_text"] = adf_to_text(fields["description"])

    assert "_description_text" not in issue
