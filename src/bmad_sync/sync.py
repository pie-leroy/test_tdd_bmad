from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .github_project import build_client_from_env


class AuthenticationError(Exception):
    """Raised when GitHub authentication fails."""


def _extract_frontmatter_value(lines: list[str], key: str) -> str | None:
    prefix = f"{key}:"
    for line in lines:
        if line.strip().startswith(prefix):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return None


def _parse_story_file(path: Path) -> tuple[str, str, str]:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    title = _extract_frontmatter_value(lines, "title")
    status = _extract_frontmatter_value(lines, "status")
    if title is None or status is None:
        raise ValueError(f"Missing frontmatter fields in {path.name}")
    story_id = path.stem
    return story_id, title, status


@dataclass(frozen=True)
class SyncResult:
    total_stories: int
    updated_stories: int


def sync_stories(*, bmad_output_dir: Path, github_client) -> SyncResult:
    github_client.validate_auth()

    story_files = sorted(p for p in bmad_output_dir.iterdir() if p.is_file() and p.suffix == ".md")
    parsed_stories = [_parse_story_file(path) for path in story_files]

    for story_id, title, status in parsed_stories:
        github_client.upsert_story(story_id=story_id, title=title, status=status)

    existing_story_ids = set(github_client.list_project_stories())
    current_story_ids = {story_id for story_id, _, _ in parsed_stories}

    for story_id in sorted(existing_story_ids - current_story_ids):
        github_client.archive_story(story_id=story_id)

    return SyncResult(total_stories=len(parsed_stories), updated_stories=len(parsed_stories))


def main() -> int:
    output_dir = Path(os.getenv("BMAD_OUTPUT_DIR", "_bmad-output/stories")).resolve()
    client = build_client_from_env()
    result = sync_stories(bmad_output_dir=output_dir, github_client=client)
    print(f"Synced {result.updated_stories}/{result.total_stories} user stories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
