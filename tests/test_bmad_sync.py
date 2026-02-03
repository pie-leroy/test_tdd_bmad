from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest

from bmad_sync.sync import AuthenticationError, SyncResult, sync_stories


@dataclass
class RecordedStory:
    story_id: str
    title: str
    status: str


class FakeGithubProjectClient:
    def __init__(self, *, valid_token: bool, existing_story_ids: list[str] | None = None) -> None:
        self._valid_token = valid_token
        self._existing_story_ids = existing_story_ids or []
        self.upserted: list[RecordedStory] = []
        self.archived: list[str] = []

    def validate_auth(self) -> None:
        if not self._valid_token:
            raise AuthenticationError("Invalid GitHub token")

    def list_project_stories(self) -> list[str]:
        return list(self._existing_story_ids)

    def upsert_story(self, *, story_id: str, title: str, status: str) -> None:
        self.upserted.append(RecordedStory(story_id=story_id, title=title, status=status))

    def archive_story(self, *, story_id: str) -> None:
        self.archived.append(story_id)


def _test_work_dir() -> Path:
    root = Path(__file__).resolve().parents[1]
    base_dir = root / ".tmp" / "bmad_sync_tests"
    test_dir = base_dir / uuid4().hex
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir


def write_story_file(directory: Path, filename: str, *, title: str, status: str) -> None:
    content = (
        "---\n"
        f'title: "{title}"\n'
        f'status: "{status}"\n'
        "---\n\n"
        f"# {title}\n"
    )
    (directory / filename).write_text(content, encoding="utf-8")


@pytest.mark.parametrize(
    "status",
    ["todo", "in_progress", "done"],
)
def test_sync_updates_project_items_for_all_bmad_stories(status: str) -> None:
    # Arrange
    test_dir = _test_work_dir()
    write_story_file(test_dir, "story-1.md", title="Story One", status=status)
    write_story_file(test_dir, "story-2.md", title="Story Two", status=status)
    client = FakeGithubProjectClient(valid_token=True)

    # Act
    result = sync_stories(bmad_output_dir=test_dir, github_client=client)

    # Assert
    assert isinstance(result, SyncResult)
    assert result.total_stories == 2
    assert result.updated_stories == 2
    assert len(client.upserted) == 2
    assert {story.story_id for story in client.upserted} == {"story-1", "story-2"}


def test_sync_handles_empty_bmad_output_gracefully() -> None:
    # Arrange
    client = FakeGithubProjectClient(valid_token=True)
    test_dir = _test_work_dir()

    # Act
    result = sync_stories(bmad_output_dir=test_dir, github_client=client)

    # Assert
    assert result.total_stories == 0
    assert result.updated_stories == 0
    assert client.upserted == []
    assert client.archived == []


def test_sync_fails_with_invalid_github_token() -> None:
    # Arrange
    test_dir = _test_work_dir()
    write_story_file(test_dir, "story-1.md", title="Story One", status="todo")
    client = FakeGithubProjectClient(valid_token=False)

    # Act / Assert
    with pytest.raises(AuthenticationError):
        sync_stories(bmad_output_dir=test_dir, github_client=client)


def test_sync_handles_deleted_or_renamed_story() -> None:
    # Arrange
    test_dir = _test_work_dir()
    write_story_file(test_dir, "story-2.md", title="Story Two", status="todo")
    client = FakeGithubProjectClient(valid_token=True, existing_story_ids=["story-1", "story-2"])

    # Act
    result = sync_stories(bmad_output_dir=test_dir, github_client=client)

    # Assert
    assert result.total_stories == 1
    assert result.updated_stories == 1
    assert client.archived == ["story-1"]
