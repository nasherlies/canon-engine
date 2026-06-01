"""Canon Engine — Encounter Bridge

Sits between free-roam and combat.  Handles the standoff phase where the
player can talk, flee, or escalate to combat.
"""
from __future__ import annotations
import random
from typing import Any

from .combat_math import d20
from .stats import get_stat_modifier


# ---------------------------------------------------------------------------
# Encounter lifecycle
# ---------------------------------------------------------------------------

def start_encounter(state: dict, encounter_data: dict) -> dict:
    """Set a pending encounter in *state* and enter standoff.

    Parameters
    ----------
    state : dict — full game state (mutable)
    encounter_data : dict — must contain at least 'enemies' list

    Returns
    -------
    dict with status and description.
    """
    state["pending_encounter"] = encounter_data
    state["encounter_status"] = "standoff"
    enemies = encounter_data.get("enemies", [])
    names = ", ".join(e.get("type", "unknown") for e in enemies)
    return {
        "status": "standoff",
        "description": f"You encounter: {names}. You can /talk, /flee, or /fight.",
    }


def resolve_talk(state: dict, rng: random.Random | None = None) -> dict:
    """Attempt to talk down enemies via a CHA check.

    DC 12  → peaceful resolution
    DC 8   → intimidate (enemies flee)
    < 8    → failed; combat begins
    """
    _rng = rng or random
    cha_mod = get_stat_modifier(state.get("stats", {}).get("CHA", 10))
    roll = d20(_rng) + cha_mod

    if roll >= 12:
        state["encounter_status"] = "none"
        state.pop("pending_encounter", None)
        return {"outcome": "peace", "description": "Your words calm the situation. The enemies stand down.", "roll": roll}

    if roll >= 8:
        state["encounter_status"] = "none"
        state.pop("pending_encounter", None)
        return {"outcome": "intimidate", "description": "Your threatening glare sends them fleeing!", "roll": roll}

    # Fail — transition to combat
    return {
        "outcome": "fail",
        "description": "Your words fall on deaf ears. Prepare for battle!",
        "roll": roll,
        **transition_to_combat(state, _rng),
    }


def resolve_flee_encounter(state: dict, rng: random.Random | None = None) -> dict:
    """Attempt to flee before combat starts. DEX check vs highest enemy DEX."""
    _rng = rng or random
    dex_mod = get_stat_modifier(state.get("stats", {}).get("DEX", 10))
    player_roll = d20(_rng) + dex_mod

    encounter = state.get("pending_encounter", {})
    enemies = encounter.get("enemies", [])
    highest_enemy_dex = max((e.get("DEX", 10) for e in enemies), default=10)
    enemy_dc = highest_enemy_dex  # raw DEX score as DC

    if player_roll >= enemy_dc:
        state["encounter_status"] = "none"
        state.pop("pending_encounter", None)
        return {"outcome": "escaped", "description": "You slip away into the shadows!", "roll": player_roll, "dc": enemy_dc}

    # Fail — combat
    return {
        "outcome": "caught",
        "description": "You couldn't outrun them!",
        "roll": player_roll,
        "dc": enemy_dc,
        **transition_to_combat(state, _rng),
    }


def transition_to_combat(state: dict, rng: random.Random | None = None) -> dict:
    """Move from standoff to combat. Returns dict consumed by start_combat."""
    state["encounter_status"] = "combat"
    return {"status": "combat", "description": "Combat begins!"}


def get_encounter_status(state: dict) -> str:
    """Return current encounter phase: 'none', 'standoff', or 'combat'."""
    return state.get("encounter_status", "none")
