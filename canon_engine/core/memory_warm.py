"""
Canon Engine — Warm Memory Module

Maintains a rolling narrative summary that the narrator uses for context.
Periodically consolidates recent events into a condensed memory block
so the LLM doesn't lose track of the story.

Public API:
    maybe_update_memory(state, narrator_result, turn) -> bool
    get_memory_prompt_block(state) -> str
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MEMORY_ROLL_EVERY_TURNS: int = 10
MAX_MEMORY_ENTRIES: int = 50  # max raw entries before forced roll
MAX_SUMMARY_LENGTH: int = 1500  # max chars for the rolling summary


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _summarize_entries(entries: List[Dict[str, Any]]) -> str:
    """Condense a list of memory entries into a text summary.

    This is a simple extractive summarizer — it concatenates the most
    important entries (those with flags or quest updates) and truncates
    the rest.  An LLM-based summarizer could replace this in production.
    """
    if not entries:
        return ""

    # Priority: quest updates, lore discoveries, combat, then regular narration
    priority_keywords = {"quest", "lore", "level", "discovered", "completed", "died", "defeated"}

    priority_entries = []
    regular_entries = []

    for entry in entries:
        text = entry.get("text", "")
        lower_text = text.lower()
        if any(kw in lower_text for kw in priority_keywords):
            priority_entries.append(entry)
        else:
            regular_entries.append(entry)

    # Build summary: priority first, then recent regular entries
    lines = []
    for entry in priority_entries[-10:]:
        turn = entry.get("turn", "?")
        lines.append(f"[T{turn}] {entry.get('text', '')[:150]}")

    for entry in regular_entries[-15:]:
        turn = entry.get("turn", "?")
        lines.append(f"[T{turn}] {entry.get('text', '')[:100]}")

    summary = "\n".join(lines)

    # Truncate if too long
    if len(summary) > MAX_SUMMARY_LENGTH:
        summary = summary[:MAX_SUMMARY_LENGTH] + "..."

    return summary


def _roll_memory(state: dict) -> None:
    """Consolidate pending entries into the rolling summary."""
    memory = state.setdefault("memory", {"summary": "", "last_update_turn": 0})
    pending = memory.get("pending", [])

    if not pending:
        return

    # Get existing summary
    existing = memory.get("summary", "")

    # Summarize new entries
    new_summary = _summarize_entries(pending)

    # Combine: existing summary + new summary
    if existing:
        combined = existing + "\n---\n" + new_summary
    else:
        combined = new_summary

    # Truncate from the front if too long (keep recent history)
    if len(combined) > MAX_SUMMARY_LENGTH:
        # Keep the last MAX_SUMMARY_LENGTH chars, cutting at a newline
        overflow = len(combined) - MAX_SUMMARY_LENGTH
        cut_idx = combined.find("\n", overflow)
        if cut_idx == -1:
            cut_idx = overflow
        combined = combined[cut_idx:].lstrip("\n")

    memory["summary"] = combined
    memory["pending"] = []


def _add_pending(state: dict, narrator_result: dict, turn: int) -> None:
    """Add a narrator result to the pending memory entries."""
    memory = state.setdefault("memory", {"summary": "", "last_update_turn": 0})
    pending = memory.setdefault("pending", [])

    entry: Dict[str, Any] = {
        "turn": turn,
        "text": narrator_result.get("narration", "")[:300],
    }

    # Enrich with metadata
    check = narrator_result.get("check")
    if check:
        entry["check"] = f"{check.get('stat', '?')} DC{check.get('dc', '?')} → {check.get('result', '?')}"

    quest = narrator_result.get("quest_update")
    if quest:
        entry["quest"] = f"{quest.get('action', '?')}: {quest.get('title', '?')}"

    lore = narrator_result.get("discovered_lore")
    if lore:
        entry["lore"] = lore.get("title", "?")

    xp = narrator_result.get("xp_add", 0)
    if xp:
        entry["xp"] = xp

    pending.append(entry)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def maybe_update_memory(state: dict, narrator_result: dict, turn: int) -> bool:
    """
    Update the rolling memory with a narrator result.

    Called every turn. Every MEMORY_ROLL_EVERY_TURNS turns, the pending
    entries are consolidated into the rolling summary.

    Parameters
    ----------
    state : dict
        The mutable game state.
    narrator_result : dict
        The narrator result from narrate_and_apply.
    turn : int
        Current turn number.

    Returns
    -------
    bool
        True if memory was rolled (consolidated), False otherwise.
    """
    # Always add to pending
    _add_pending(state, narrator_result, turn)

    memory = state.setdefault("memory", {"summary": "", "last_update_turn": 0})
    last_roll = memory.get("last_update_turn", 0)
    pending = memory.get("pending", [])

    # Roll if enough turns have passed or too many pending entries
    should_roll = (
        (turn - last_roll) >= MEMORY_ROLL_EVERY_TURNS
        or len(pending) >= MAX_MEMORY_ENTRIES
    )

    if should_roll:
        _roll_memory(state)
        memory["last_update_turn"] = turn
        return True

    return False


def get_memory_prompt_block(state: dict) -> str:
    """
    Get the memory summary as text for the narrator's system prompt.

    Parameters
    ----------
    state : dict
        The game state.

    Returns
    -------
    str
        Formatted memory text, or empty string if no memory exists.
    """
    memory = state.get("memory", {})
    if isinstance(memory, list): memory = {"summary": "", "last_summary_turn": 0, "pending": []}
    if isinstance(memory, list): memory = {"summary": "", "last_summary_turn": 0, "pending": []}
    summary = memory.get("summary", "")
    pending = memory.get("pending", [])

    parts = []

    if summary:
        parts.append(summary)

    # Include recent pending entries too for immediate context
    if pending:
        recent = pending[-5:]
        pending_lines = []
        for entry in recent:
            turn = entry.get("turn", "?")
            text = entry.get("text", "")[:120]
            pending_lines.append(f"[T{turn}] {text}")
        if pending_lines:
            parts.append("Recent:\n" + "\n".join(pending_lines))

    return "\n".join(parts) if parts else ""


def clear_memory(state: dict) -> None:
    """Clear all memory (for testing or new game)."""
    state["memory"] = {"summary": "", "last_update_turn": 0}
