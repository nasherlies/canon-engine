"""Canon Engine — Interactive Tutorial System

Guides new players through core mechanics step by step.
Loads tutorial steps from content/tutorial/tutorial_steps.json.

Public API:
    load_tutorial_steps() -> list[dict]
    build_tutorial_session_state(state) -> None
    advance_tutorial(state, command_kind) -> dict
    get_tutorial_step(state) -> dict | None
    tutorial_active(state) -> bool
    exit_tutorial(state) -> None
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

_STEPS_PATH = _CONTENT_DIR / "tutorial" / "tutorial_steps.json"

# Map command_kind to trigger keywords found in completion_trigger strings
_COMMAND_TO_TRIGGER: dict[str, list[str]] = {
    "look": ["look", "movement"],
    "inv": ["inventory", "inv", "checked_inventory"],
    "attack": ["combat", "defeated_enemy", "attack"],
    "skills": ["skill"],
    "quest": ["quest", "accepted_quest"],
    "save": ["save", "saved_game"],
    "npc": ["talk", "npc", "talked_to_npc"],
    "crafting": ["craft", "recipe", "crafting", "viewed_recipes"],
    "say": ["say"],
    "do": ["do"],
    "move": ["move", "moved", "location", "moved_to_location"],
    "travel": ["move", "moved", "location", "moved_to_location"],
    "loot": ["loot", "looted", "looted_corpse"],
    "dismiss": ["dismiss", "complete", "exit", "dismissed_tutorial"],
}


def load_tutorial_steps() -> list[dict]:
    """Load tutorial steps from content/tutorial/tutorial_steps.json.

    Returns the list of step dicts.  Falls back to a minimal set if the
    content file is missing.
    """
    if _STEPS_PATH.exists():
        data = json.loads(_STEPS_PATH.read_text(encoding="utf-8"))
        return data.get("tutorial_steps", [])

    # Fallback: minimal inline steps
    return [
        {"id": "welcome", "header": "Welcome", "instructions": "Welcome to Canon Engine!", "completion_trigger": "any"},
        {"id": "movement", "header": "Movement", "instructions": "Type /look to see your surroundings.", "completion_trigger": "player_used_look"},
        {"id": "inventory", "header": "Inventory", "instructions": "Type /inv to check your gear.", "completion_trigger": "player_checked_inventory"},
        {"id": "combat", "header": "Combat", "instructions": "Type /attack to engage an enemy.", "completion_trigger": "player_defeated_enemy"},
        {"id": "skills", "header": "Skills", "instructions": "Type /skills to view your abilities.", "completion_trigger": "player_viewed_skills"},
        {"id": "quest", "header": "Quests", "instructions": "Accept a quest to continue.", "completion_trigger": "player_accepted_quest"},
        {"id": "save", "header": "Save", "instructions": "Type /save to save your game.", "completion_trigger": "player_saved_game"},
        {"id": "npc", "header": "NPCs", "instructions": "Type /talk to speak with an NPC.", "completion_trigger": "player_talked_to_npc"},
        {"id": "crafting", "header": "Crafting", "instructions": "Type /craft to see recipes.", "completion_trigger": "player_viewed_recipes"},
        {"id": "complete", "header": "Complete!", "instructions": "You're ready to adventure!", "completion_trigger": "player_dismissed_tutorial"},
    ]


# ── Tutorial state management ───────────────────────────────────────────────

def build_tutorial_session_state(state: dict[str, Any]) -> None:
    """Activate the tutorial and initialize tutorial tracking in state.

    Sets state["tutorial"] with active flag, current step index, and
    the loaded step list.
    """
    steps = load_tutorial_steps()
    state["tutorial"] = {
        "active": True,
        "step_index": 0,
        "steps": steps,
        "completed_steps": [],
    }


_SPECIAL_TRIGGERS: set[str] = {
    "player_provides_name", "stats_assigned", "player_dismissed_tutorial",
}


def _matches_trigger(command_kind: str, trigger: str) -> bool:
    """Check if a command_kind matches a tutorial step's completion_trigger."""
    if trigger == "any":
        return True

    # Special triggers that accept any command (player_provides_name, stats_assigned, etc.)
    if trigger in _SPECIAL_TRIGGERS:
        return True

    # Direct match
    if command_kind == trigger:
        return True

    # Check mapped keywords
    keywords = _COMMAND_TO_TRIGGER.get(command_kind, [])
    for kw in keywords:
        if kw in trigger:
            return True

    # Fuzzy: command_kind substring in trigger
    if command_kind.lower() in trigger.lower():
        return True

    return False


def advance_tutorial(state: dict[str, Any], command_kind: str) -> dict:
    """Advance the tutorial if the current step's criteria are met.

    Parameters
    ----------
    state : dict
        Mutable game state.
    command_kind : str
        The kind of command the player just executed (e.g. "look", "inv", "attack").

    Returns
    -------
    dict
        Result with keys: advanced, current_step, message, tutorial_complete.
    """
    tut = state.get("tutorial", {})
    if not tut.get("active", False):
        return {"advanced": False, "reason": "Tutorial not active."}

    steps = tut.get("steps", [])
    idx = tut.get("step_index", 0)

    if idx >= len(steps):
        return {"advanced": False, "reason": "Tutorial already complete.", "tutorial_complete": True}

    current_step = steps[idx]
    trigger = current_step.get("completion_trigger", "any")

    if not _matches_trigger(command_kind, trigger):
        return {
            "advanced": False,
            "current_step": current_step.get("id", ""),
            "message": f"Current step requires: {trigger}",
            "tutorial_complete": False,
        }

    # Mark step complete
    tut.setdefault("completed_steps", []).append(current_step.get("id", ""))
    idx += 1
    tut["step_index"] = idx

    if idx >= len(steps):
        tut["active"] = False
        return {
            "advanced": True,
            "current_step": "complete",
            "message": "Tutorial complete! You're ready to adventure.",
            "tutorial_complete": True,
        }

    next_step = steps[idx]
    return {
        "advanced": True,
        "current_step": next_step.get("id", ""),
        "message": next_step.get("instructions", ""),
        "tutorial_complete": False,
    }


def get_tutorial_step(state: dict[str, Any]) -> dict | None:
    """Return the current tutorial step dict, or None if tutorial inactive."""
    tut = state.get("tutorial", {})
    if not tut.get("active", False):
        return None

    steps = tut.get("steps", [])
    idx = tut.get("step_index", 0)
    if idx >= len(steps):
        return None
    return steps[idx]


def tutorial_active(state: dict[str, Any]) -> bool:
    """Return True if the tutorial is currently active."""
    return state.get("tutorial", {}).get("active", False)


def exit_tutorial(state: dict[str, Any]) -> None:
    """Deactivate the tutorial, allowing free play."""
    state["tutorial"] = {"active": False}
