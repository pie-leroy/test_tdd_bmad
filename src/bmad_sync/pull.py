from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .github_project import build_client_from_env


@dataclass(frozen=True)
class PullResult:
    total_items: int
    written_stories: int


@dataclass(frozen=True)
class StoryRecord:
    story_id: str
    title: str
    status: str


def _normalize_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized == "todo":
        return "todo"
    if normalized in {"in progress", "in_progress", "in-progress"}:
        return "in_progress"
    if normalized == "done":
        return "done"
    return normalized.replace(" ", "_")


def _split_frontmatter(content: str) -> tuple[list[str] | None, list[str]]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, lines
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return lines[1:idx], lines[idx + 1 :]
    return None, lines


def _build_frontmatter(*, title: str, status: str, existing: list[str] | None) -> list[str]:
    filtered = []
    if existing:
        for line in existing:
            stripped = line.strip().lower()
            if stripped.startswith("title:") or stripped.startswith("status:"):
                continue
            filtered.append(line)
    frontmatter = [f'title: "{title}"', f'status: "{status}"']
    frontmatter.extend(filtered)
    return frontmatter


def _render_story_content(*, title: str, status: str, existing_content: str | None) -> str:
    if existing_content:
        frontmatter, body_lines = _split_frontmatter(existing_content)
    else:
        frontmatter, body_lines = None, []

    frontmatter_lines = _build_frontmatter(title=title, status=status, existing=frontmatter)
    if not body_lines:
        body_lines = [f"# {title}", ""]
    output_lines: list[str] = ["---", *frontmatter_lines, "---", "", *body_lines]
    return "\n".join(output_lines).rstrip() + "\n"


def pull_stories(*, bmad_output_dir: Path, github_client) -> PullResult:
    github_client.validate_auth()

    bmad_output_dir.mkdir(parents=True, exist_ok=True)
    stories = github_client.list_project_story_details()

    written = 0
    for story in stories:
        target = bmad_output_dir / f"{story.story_id}.md"
        existing = target.read_text(encoding="utf-8") if target.exists() else None
        content = _render_story_content(
            title=story.title,
            status=_normalize_status(story.status),
            existing_content=existing,
        )
        target.write_text(content, encoding="utf-8")
        written += 1

    return PullResult(total_items=len(stories), written_stories=written)


def main() -> int:
    output_dir = Path(os.getenv("BMAD_OUTPUT_DIR", "_bmad-output/stories")).resolve()
    client = build_client_from_env()
    result = pull_stories(bmad_output_dir=output_dir, github_client=client)
    print(f"Pulled {result.written_stories}/{result.total_items} user stories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
