from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import request


class AuthenticationError(Exception):
    """Raised when GitHub authentication fails."""


class GitHubApiError(Exception):
    """Raised when GitHub GraphQL API returns an error."""


@dataclass(frozen=True)
class ProjectItem:
    item_id: str
    story_id: str


@dataclass(frozen=True)
class StatusOptions:
    todo: str
    in_progress: str
    done: str


class GitHubProjectClient:
    def __init__(
        self,
        *,
        token: str,
        project_id: str,
        status_field_id: str,
        status_options: StatusOptions,
    ) -> None:
        self._token = token
        self._project_id = project_id
        self._status_field_id = status_field_id
        self._status_options = status_options

    def validate_auth(self) -> None:
        self._graphql("query { viewer { login } }")

    def list_project_stories(self) -> list[str]:
        items = self._list_project_items()
        return [item.story_id for item in items]

    def upsert_story(self, *, story_id: str, title: str, status: str) -> None:
        items = self._list_project_items()
        existing = next((item for item in items if item.story_id == story_id), None)
        if existing is None:
            item_id = self._add_draft_issue(title=f"[{story_id}] {title}")
        else:
            item_id = existing.item_id
        self._update_status(item_id=item_id, status=status)

    def archive_story(self, *, story_id: str) -> None:
        items = self._list_project_items()
        existing = next((item for item in items if item.story_id == story_id), None)
        if existing is None:
            return
        self._archive_item(item_id=existing.item_id)

    def _list_project_items(self) -> list[ProjectItem]:
        query = (
            "query($projectId:ID!) {"
            "  node(id:$projectId) {"
            "    ... on ProjectV2 {"
            "      items(first:100) {"
            "        nodes {"
            "          id"
            "          content {"
            "            ... on DraftIssue { title }"
            "            ... on Issue { title }"
            "          }"
            "          title"
            "        }"
            "      }"
            "    }"
            "  }"
            "}"
        )
        data = self._graphql(query, variables={"projectId": self._project_id})
        nodes = (
            data.get("data", {})
            .get("node", {})
            .get("items", {})
            .get("nodes", [])
        )
        items: list[ProjectItem] = []
        for node in nodes:
            title = self._extract_title(node)
            story_id = self._extract_story_id(title)
            if story_id:
                items.append(ProjectItem(item_id=node["id"], story_id=story_id))
        return items

    def _add_draft_issue(self, *, title: str) -> str:
        query = (
            "mutation($projectId:ID!, $title:String!) {"
            "  addProjectV2DraftIssue(input:{projectId:$projectId, title:$title}) {"
            "    projectItem { id }"
            "  }"
            "}"
        )
        data = self._graphql(query, variables={"projectId": self._project_id, "title": title})
        return data["data"]["addProjectV2DraftIssue"]["projectItem"]["id"]

    def _update_status(self, *, item_id: str, status: str) -> None:
        option_id = self._status_option_id(status)
        query = (
            "mutation($projectId:ID!, $itemId:ID!, $fieldId:ID!, $optionId:String!) {"
            "  updateProjectV2ItemFieldValue("
            "    input:{projectId:$projectId, itemId:$itemId, fieldId:$fieldId, value:{singleSelectOptionId:$optionId}}"
            "  ) {"
            "    projectV2Item { id }"
            "  }"
            "}"
        )
        self._graphql(
            query,
            variables={
                "projectId": self._project_id,
                "itemId": item_id,
                "fieldId": self._status_field_id,
                "optionId": option_id,
            },
        )

    def _archive_item(self, *, item_id: str) -> None:
        query = (
            "mutation($projectId:ID!, $itemId:ID!) {"
            "  archiveProjectV2Item(input:{projectId:$projectId, itemId:$itemId}) {"
            "    projectV2Item { id }"
            "  }"
            "}"
        )
        self._graphql(query, variables={"projectId": self._project_id, "itemId": item_id})

    def _status_option_id(self, status: str) -> str:
        normalized = status.strip().lower()
        if normalized == "todo":
            return self._status_options.todo
        if normalized in {"in_progress", "in-progress"}:
            return self._status_options.in_progress
        if normalized == "done":
            return self._status_options.done
        raise ValueError(f"Unsupported status value: {status}")

    def _graphql(self, query: str, *, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"query": query, "variables": variables or {}}
        data = json.dumps(payload).encode("utf-8")
        req = request.Request("https://api.github.com/graphql", data=data)
        req.add_header("Authorization", f"Bearer {self._token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("Content-Type", "application/json")
        with request.urlopen(req) as response:
            body = response.read().decode("utf-8")
            result = json.loads(body)
        if "errors" in result:
            messages = ", ".join(error.get("message", "Unknown error") for error in result["errors"])
            if "Bad credentials" in messages:
                raise AuthenticationError(messages)
            raise GitHubApiError(messages)
        return result

    @staticmethod
    def _extract_title(node: dict[str, Any]) -> str:
        content = node.get("content") or {}
        title = content.get("title") or node.get("title") or ""
        return title

    @staticmethod
    def _extract_story_id(title: str) -> str | None:
        if title.startswith("[") and "]" in title:
            return title.split("]", 1)[0].lstrip("[")
        return None


def build_client_from_env() -> GitHubProjectClient:
    token = _required_env("GITHUB_TOKEN")
    project_id = _required_env("GITHUB_PROJECT_ID")
    status_field_id = _required_env("GITHUB_STATUS_FIELD_ID")
    status_options = StatusOptions(
        todo=_required_env("GITHUB_STATUS_TODO_ID"),
        in_progress=_required_env("GITHUB_STATUS_IN_PROGRESS_ID"),
        done=_required_env("GITHUB_STATUS_DONE_ID"),
    )
    return GitHubProjectClient(
        token=token,
        project_id=project_id,
        status_field_id=status_field_id,
        status_options=status_options,
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value
