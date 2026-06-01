"""Canon Engine — Narrative Journal

Builds a structured journal payload from world_log, rolling memory,
quests, and chapter markers for display in the UI.

Public API:
    build_journal_payload(state) -> dict
    format_journal(state) -> str
"""

from __future__ import annotations

from typing import Any


# ── Chapter marker detection ────────────────────────────────────────────────

_CHAPTER_KEYWORDS = {
    "chapter", "act", "quest completed", "level up", "boss defeated",
    "new area discovered", "major choice", "death", "rebirth",
}


def _extract_chapter_markers(world_log: list[dict]) -> list[dict]:
    """Scan world_log for significant events to mark as chapter boundaries."""
    markers: list[dict] = []
    for entry in world_log:
        text = entry.get("text", "").lower()
        turn = entry.get("turn", 0)
        for kw in _CHAPTER_KEYWORDS:
            if kw in text:
                markers.append({
                    "turn": turn,
                    "keyword": kw,
                    "text": entry.get("text", "")[:120],
                })
                break
    return markers


# ── Quest summary ───────────────────────────────────────────────────────────

def _build_quest_summary(state: dict[str, Any]) -> dict:
    """Summarize active, completed, and failed quests."""
    quests = state.get("world", {}).get("quests", {})
    active = quests.get("active", {})
    completed = quests.get("completed", {})
    failed = quests.get("failed", {})

    return {
        "active": [
            {"id": qid, "name": q.get("name", qid), "description": q.get("description", "")}
            for qid, q in active.items()
        ],
        "completed": [
            {"id": qid, "name": q.get("name", qid)}
            for qid, q in completed.items()
        ],
        "failed": [
            {"id": qid, "name": q.get("name", qid)}
            for qid, q in failed.items()
        ],
    }


# ── Public API ──────────────────────────────────────────────────────────────

def build_journal_payload(state: dict[str, Any]) -> dict:
    """Build a structured journal payload.

    Combines:
    - world_log tail (last 30 entries)
    - rolling memory summary
    - quest summaries
    - chapter markers

    Returns a dict suitable for JSON serialization / UI rendering.
    """
    world_log = state.get("world_log", [])
    memory = state.get("memory", {})

    return {
        "world_log_tail": world_log[-30:],
        "rolling_memory": memory.get("summary", ""),
        "quests": _build_quest_summary(state),
        "chapter_markers": _extract_chapter_markers(world_log),
        "total_entries": len(world_log),
        "turn": state.get("turn", 0),
    }


def format_journal(state: dict[str, Any]) -> str:
    """Format the journal as a human-readable string for display."""
    payload = build_journal_payload(state)
    lines: list[str] = []

    # Header
    lines.append("═══ **Chronicle Journal** ═══")
    lines.append(f"Turn {payload['turn']} · {payload['total_entries']} entries recorded")
    lines.append("")

    # Rolling memory
    memory = payload["rolling_memory"]
    if memory:
        lines.append("📖 **Running Memory**")
        lines.append(memory[:500])
        lines.append("")

    # Chapter markers
    markers = payload["chapter_markers"]
    if markers:
        lines.append("📑 **Chapter Markers**")
        for m in markers[-5:]:  # last 5
            lines.append(f"  • Turn {m['turn']}: {m['text']}")
        lines.append("")

    # Quests
    quests = payload["quests"]
    if quests["active"]:
        lines.append("⚔️ **Active Quests**")
        for q in quests["active"]:
            lines.append(f"  • {q['name']}: {q['description'][:80]}")
        lines.append("")
    if quests["completed"]:
        lines.append("✅ **Completed Quests**")
        for q in quests["completed"]:
            lines.append(f"  • {q['name']}")
        lines.append("")
    if quests["failed"]:
        lines.append("❌ **Failed Quests**")
        for q in quests["failed"]:
            lines.append(f"  • {q['name']}")
        lines.append("")

    # Recent log
    tail = payload["world_log_tail"]
    if tail:
        lines.append("📜 **Recent Events**")
        for entry in tail[-10:]:
            turn = entry.get("turn", "?")
            text = entry.get("text", "")
            lines.append(f"  [{turn}] {text[:120]}")
    else:
        lines.append("📜 The journal is empty. Your story has yet to begin.")

    return "\n".join(lines)
