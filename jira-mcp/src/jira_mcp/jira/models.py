"""Pydantic models for Jira API responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class JiraUser(BaseModel):
    account_id: str = Field(alias="accountId", default="")
    display_name: str = Field(alias="displayName", default="")
    email_address: str | None = Field(alias="emailAddress", default=None)

    model_config = {"populate_by_name": True}


class JiraIssueFields(BaseModel):
    summary: str = ""
    description: Any | None = None
    status: dict[str, Any] | None = None
    issue_type: dict[str, Any] | None = Field(alias="issuetype", default=None)
    priority: dict[str, Any] | None = None
    assignee: JiraUser | None = None
    reporter: JiraUser | None = None
    labels: list[str] = Field(default_factory=list)
    project: dict[str, Any] | None = None
    created: str | None = None
    updated: str | None = None
    comment: dict[str, Any] | None = None

    model_config = {"populate_by_name": True}


class JiraIssue(BaseModel):
    id: str = ""
    key: str = ""
    self_url: str = Field(alias="self", default="")
    fields: JiraIssueFields = Field(default_factory=JiraIssueFields)

    model_config = {"populate_by_name": True}


class JiraSearchResult(BaseModel):
    start_at: int = Field(alias="startAt", default=0)
    max_results: int = Field(alias="maxResults", default=50)
    total: int = 0
    issues: list[JiraIssue] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class JiraProject(BaseModel):
    id: str = ""
    key: str = ""
    name: str = ""
    project_type_key: str | None = Field(alias="projectTypeKey", default=None)
    self_url: str = Field(alias="self", default="")

    model_config = {"populate_by_name": True}


class JiraTransition(BaseModel):
    id: str = ""
    name: str = ""
    to: dict[str, Any] | None = None

    model_config = {"populate_by_name": True}


class JiraComment(BaseModel):
    id: str = ""
    author: JiraUser | None = None
    body: Any | None = None
    created: str | None = None
    updated: str | None = None

    model_config = {"populate_by_name": True}
