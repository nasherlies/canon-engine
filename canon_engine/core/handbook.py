"""Canon Engine — In-Game Handbook / Manual

Loads handbook topics from content/handbook/topics.json and optionally
incorporates changelog sections from canonchanges.md.

Public API:
    load_handbook_topics() -> list[dict]
    get_handbook_index() -> list[dict]
    get_handbook_topic(topic_id) -> dict
    format_handbook(state) -> str
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


# ── Content loader ──────────────────────────────────────────────────────────

_CONTENT_DIR = Path(os.environ.get(
    "CANON_CONTENT_DIR",
    Path(__file__).resolve().parents[2] / "content",
))

_TOPICS_PATH = _CONTENT_DIR / "handbook" / "topics.json"
_CHANGELOG_PATH = _CONTENT_DIR.parent / "canonchanges.md"

# Cache for loaded topics
_topics_cache: list[dict] | None = None


def _parse_changelog_sections(path: Path) -> list[dict]:
    """Parse canonchanges.md into handbook topic entries."""
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    sections: list[dict] = []
    current_title: str | None = None
    current_body_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            # Flush previous section
            if current_title:
                sections.append({
                    "id": f"changelog_{current_title.lower().replace(' ', '_')[:30]}",
                    "title": f"📋 {current_title}",
                    "body": "\n".join(current_body_lines).strip(),
                })
            current_title = stripped[3:].strip()
            current_body_lines = []
        elif current_title:
            current_body_lines.append(line)

    # Flush last section
    if current_title:
        sections.append({
            "id": f"changelog_{current_title.lower().replace(' ', '_')[:30]}",
            "title": f"📋 {current_title}",
            "body": "\n".join(current_body_lines).strip(),
        })

    return sections


# ── Public API ──────────────────────────────────────────────────────────────

def load_handbook_topics() -> list[dict]:
    """Load handbook topics from content/handbook/topics.json.

    Appends changelog sections from canonchanges.md if present.
    Results are cached after first load.

    Returns a list of topic dicts, each with 'id', 'title', 'body'.
    """
    global _topics_cache
    if _topics_cache is not None:
        return list(_topics_cache)

    topics: list[dict] = []

    # Load main topics
    if _TOPICS_PATH.exists():
        data = json.loads(_TOPICS_PATH.read_text(encoding="utf-8"))
        topics = data.get("topics", [])

    # Append changelog sections
    topics.extend(_parse_changelog_sections(_CHANGELOG_PATH))

    _topics_cache = topics
    return list(topics)


def get_handbook_index() -> list[dict]:
    """Return a lightweight index of all handbook topics.

    Each entry has 'id' and 'title' only (no body).
    """
    topics = load_handbook_topics()
    return [{"id": t["id"], "title": t["title"]} for t in topics]


def get_handbook_topic(topic_id: str) -> dict:
    """Look up a single topic by id.

    Returns the topic dict with 'id', 'title', 'body'.
    If not found, returns a fallback dict with an error message.
    """
    topics = load_handbook_topics()
    for t in topics:
        if t["id"] == topic_id:
            return dict(t)

    # Fallback: fuzzy search
    topic_lower = topic_id.lower()
    for t in topics:
        if topic_lower in t["id"].lower() or topic_lower in t.get("title", "").lower():
            return dict(t)

    return {
        "id": topic_id,
        "title": "Not Found",
        "body": f"Topic '{topic_id}' not found in the handbook. Use the index to browse available topics.",
    }


def format_handbook(state: dict[str, Any]) -> str:
    """Format the full handbook for display.

    If state has a 'handbook_topic' key, shows that specific topic.
    Otherwise shows the full index.
    """
    topic_id = state.get("handbook_topic", "")
    if topic_id:
        topic = get_handbook_topic(topic_id)
        return f"📖 **{topic['title']}**\n\n{topic['body']}"

    # Show index
    index = get_handbook_index()
    lines = ["📖 **Canon Engine Handbook**\n"]
    for i, entry in enumerate(index, 1):
        lines.append(f"  {i}. **{entry['title']}** (`{entry['id']}`)")
    lines.append("\nUse `/handbook <topic_id>` to read a specific topic.")
    return "\n".join(lines)
