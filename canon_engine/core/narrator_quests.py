"""
Canon Engine — Narrator-Driven Quest System

Handles AI-generated free-text quest updates from the narrator.
Quests here are freeform (not template-based) and can be created,
advanced, completed, or failed by narrator payloads.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_MAX_UPDATES_PER_TURN = 3


# ── State helpers ─────────────────────────────────────────────────────

def _ensure_narrator_quests(state: dict[str, Any]) -> None:
    """Ensure narrator quest storage exists in state."""
    state.setdefault("narrator_quests", [])
    state.setdefault("narrator_quests_completed", [])
    state.setdefault("narrator_quests_failed", [])
    state.setdefault("quest_pulse", [])


def _find_quest(state: dict[str, Any], quest_id: str) -> dict | None:
    """Find a narrator quest by id."""
    for q in state.get("narrator_quests", []):
        if q.get("id") == quest_id:
            return q
    return None


# ── Main apply function ──────────────────────────────────────────────

def apply_quest_update_payload(
    state: dict[str, Any],
    updates: list[dict] | dict,
    turn: int = 0,
) -> list[str]:
    """Handle quest_update or quest_update_many from narrator.

    Each update dict has an 'action' field:
      - new_quest: create quest with free-text objectives
      - objective_complete: flip objective.completed by index or text match
      - quest_complete: archive quest, auto-link to codex
      - quest_fail: archive as failed

    Returns list of log lines.
    """
    _ensure_narrator_quests(state)

    if isinstance(updates, dict):
        updates = [updates]

    # Cap at 3 per turn
    updates = updates[:_MAX_UPDATES_PER_TURN]

    log_lines: list[str] = []
    pulse = state.setdefault("quest_pulse", [])

    for upd in updates:
        action = upd.get("action", "")

        if action == "new_quest":
            quest_id = upd.get("id") or f"nq_{len(state['narrator_quests']) + len(state['narrator_quests_completed']) + len(state['narrator_quests_failed']) + 1}"
            objectives_raw = upd.get("objectives", [])
            objectives = []
            for obj in objectives_raw:
                if isinstance(obj, str):
                    objectives.append({"text": obj, "completed": False})
                elif isinstance(obj, dict):
                    objectives.append({
                        "text": obj.get("text", ""),
                        "completed": obj.get("completed", False),
                    })

            quest = {
                "id": quest_id,
                "title": upd.get("title", "Unnamed Quest"),
                "giver": upd.get("giver", ""),
                "type": "narrator",
                "objectives": objectives,
                "reward": upd.get("reward", {}),
                "status": "active",
                "discovered_at": turn,
                "expires_at": upd.get("expires_at"),
            }
            state["narrator_quests"].append(quest)
            log_lines.append(f"[QUEST] New quest: {quest['title']}")
            pulse.append({"type": "new_quest", "quest_id": quest_id, "title": quest["title"], "turn": turn})

        elif action == "objective_complete":
            quest_id = upd.get("quest_id", "")
            quest = _find_quest(state, quest_id)
            if quest is None:
                log_lines.append(f"[QUEST] Quest '{quest_id}' not found for objective_complete.")
                continue

            idx = upd.get("objective_index")
            text_match = upd.get("objective_text", "")
            completed = False

            if idx is not None and 0 <= idx < len(quest["objectives"]):
                quest["objectives"][idx]["completed"] = True
                completed = True
            elif text_match:
                for obj in quest["objectives"]:
                    if text_match.lower() in obj.get("text", "").lower():
                        obj["completed"] = True
                        completed = True
                        break

            if completed:
                log_lines.append(f"[QUEST] Objective completed in '{quest['title']}'")
                pulse.append({"type": "objective_complete", "quest_id": quest_id, "turn": turn})
            else:
                log_lines.append(f"[QUEST] No matching objective found in '{quest_id}'")

        elif action == "quest_complete":
            quest_id = upd.get("quest_id", "")
            quest = _find_quest(state, quest_id)
            if quest is None:
                log_lines.append(f"[QUEST] Quest '{quest_id}' not found for quest_complete.")
                continue

            # Mark all objectives complete
            for obj in quest.get("objectives", []):
                obj["completed"] = True

            quest["status"] = "completed"
            state["narrator_quests"] = [
                q for q in state["narrator_quests"] if q.get("id") != quest_id
            ]
            state["narrator_quests_completed"].append(quest)

            # Auto-link to codex
            _maybe_link_codex(state, quest, turn)

            log_lines.append(f"[QUEST] Quest completed: {quest['title']}")
            pulse.append({"type": "quest_complete", "quest_id": quest_id, "title": quest["title"], "turn": turn})

        elif action == "quest_fail":
            quest_id = upd.get("quest_id", "")
            quest = _find_quest(state, quest_id)
            if quest is None:
                log_lines.append(f"[QUEST] Quest '{quest_id}' not found for quest_fail.")
                continue

            quest["status"] = "failed"
            state["narrator_quests"] = [
                q for q in state["narrator_quests"] if q.get("id") != quest_id
            ]
            state["narrator_quests_failed"].append(quest)

            log_lines.append(f"[QUEST] Quest failed: {quest['title']}")
            pulse.append({"type": "quest_fail", "quest_id": quest_id, "title": quest["title"], "turn": turn})

        else:
            log_lines.append(f"[QUEST] Unknown quest action: '{action}'")

    return log_lines


# ── Prompt block ──────────────────────────────────────────────────────

def narrator_quests_prompt_block(state: dict[str, Any], max_chars: int = 700) -> str:
    """Build compact quest summary for system prompt inclusion."""
    _ensure_narrator_quests(state)
    active = state.get("narrator_quests", [])
    if not active:
        return ""

    lines = ["## Active Quests"]
    for q in active:
        title = q.get("title", "Unknown")
        objs = q.get("objectives", [])
        done = sum(1 for o in objs if o.get("completed"))
        total = len(objs)
        line = f"- {title} [{done}/{total}]"
        # Add incomplete objectives
        for o in objs:
            if not o.get("completed"):
                line += f"\n  - {o.get('text', '?')}"
        lines.append(line)

    result = "\n".join(lines)
    if len(result) > max_chars:
        result = result[:max_chars - 3] + "..."
    return result


# ── API payload ───────────────────────────────────────────────────────

def quest_log_payload(state: dict[str, Any]) -> dict:
    """Return full quest log for API consumption."""
    _ensure_narrator_quests(state)
    return {
        "active": [
            {
                "id": q.get("id"),
                "title": q.get("title"),
                "objectives": q.get("objectives", []),
                "giver": q.get("giver", ""),
                "discovered_at": q.get("discovered_at"),
            }
            for q in state.get("narrator_quests", [])
        ],
        "completed": [
            {"id": q.get("id"), "title": q.get("title")}
            for q in state.get("narrator_quests_completed", [])
        ],
        "failed": [
            {"id": q.get("id"), "title": q.get("title")}
            for q in state.get("narrator_quests_failed", [])
        ],
    }


# ── Pulse (per-turn events) ──────────────────────────────────────────

def drain_quest_pulse(state: dict[str, Any]) -> list[dict]:
    """Read and clear per-turn quest events."""
    pulse = state.get("quest_pulse", [])
    state["quest_pulse"] = []
    return pulse


# ── Codex auto-link ───────────────────────────────────────────────────

def _maybe_link_codex(state: dict[str, Any], quest: dict, turn: int) -> None:
    """Auto-promote quest giver to codex card if they aren't already there."""
    giver = quest.get("giver", "")
    if not giver:
        return

    try:
        from canon_engine.core.lore_codex import ensure_codex, discover_card
        ensure_codex(state)
        # Check if already in codex
        cards = state.get("lore_cards", [])
        existing_ids = {c.get("id") for c in cards}
        from canon_engine.core.lore_codex import slug_for
        card_id = slug_for(giver, "character")
        if card_id not in existing_ids:
            discover_card(state, {
                "title": giver,
                "category": "character",
                "description": f"A figure who entrusted you with a quest.",
                "locked": False,
            }, turn=turn, source="quest_auto")
    except (ImportError, AttributeError):
        pass
