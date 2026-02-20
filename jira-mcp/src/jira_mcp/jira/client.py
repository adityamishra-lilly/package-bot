"""Async Jira REST API v3 client using httpx."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from jira_mcp.jira.errors import (
    JiraAPIError,
    JiraAuthenticationError,
    JiraNotFoundError,
    JiraPermissionError,
    JiraValidationError,
)

logger = logging.getLogger("jira_mcp")

_ERROR_MAP: dict[int, type[JiraAPIError]] = {
    400: JiraValidationError,
    401: JiraAuthenticationError,
    403: JiraPermissionError,
    404: JiraNotFoundError,
}


class JiraClient:
    """Async wrapper around Jira REST API v3."""

    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        timeout: int = 30,
        ssl_verify: bool | str = True,
    ):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=f"{self._base_url}/rest/api/3",
            auth=(email, api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=timeout,
            verify=ssl_verify,
        )

    async def close(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Request helpers
    # ------------------------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = await self._client.request(method, path, **kwargs)
        if response.status_code >= 400:
            body = response.text
            error_cls = _ERROR_MAP.get(response.status_code, JiraAPIError)
            raise error_cls(f"Jira API {method} {path} failed ({response.status_code}): {body}")
        if response.status_code == 204:
            return None
        return response.json()

    async def _get(self, path: str, **params: Any) -> Any:
        return await self._request("GET", path, params=params)

    async def _post(self, path: str, json: Any) -> Any:
        return await self._request("POST", path, json=json)

    async def _put(self, path: str, json: Any) -> Any:
        return await self._request("PUT", path, json=json)

    async def _delete(self, path: str) -> Any:
        return await self._request("DELETE", path)

    # ------------------------------------------------------------------
    # Issues
    # ------------------------------------------------------------------

    async def get_issue(self, issue_key: str) -> dict[str, Any]:
        return await self._get(f"/issue/{issue_key}")

    async def create_issue(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/issue", json={"fields": fields})

    async def update_issue(self, issue_key: str, fields: dict[str, Any]) -> None:
        await self._put(f"/issue/{issue_key}", json={"fields": fields})

    async def delete_issue(self, issue_key: str) -> None:
        await self._delete(f"/issue/{issue_key}")

    async def assign_issue(self, issue_key: str, account_id: str | None) -> None:
        await self._put(f"/issue/{issue_key}/assignee", json={"accountId": account_id})

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search_issues(
        self, jql: str, max_results: int = 50, start_at: int = 0
    ) -> dict[str, Any]:
        return await self._post(
            "/search",
            json={"jql": jql, "maxResults": max_results, "startAt": start_at},
        )

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    async def get_comments(self, issue_key: str) -> dict[str, Any]:
        return await self._get(f"/issue/{issue_key}/comment")

    async def add_comment(self, issue_key: str, body: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"/issue/{issue_key}/comment", json={"body": body})

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    async def get_transitions(self, issue_key: str) -> dict[str, Any]:
        return await self._get(f"/issue/{issue_key}/transitions")

    async def transition_issue(
        self, issue_key: str, transition_id: str, fields: dict[str, Any] | None = None
    ) -> None:
        payload: dict[str, Any] = {"transition": {"id": transition_id}}
        if fields:
            payload["fields"] = fields
        await self._post(f"/issue/{issue_key}/transitions", json=payload)

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    async def list_projects(self) -> list[dict[str, Any]]:
        return await self._get("/project")

    async def get_project(self, project_key: str) -> dict[str, Any]:
        return await self._get(f"/project/{project_key}")
