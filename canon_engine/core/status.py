"""Canon Engine — Status Effects System

STATUS_REGISTRY defines every status that can be applied to a character.
Each entry specifies duration behaviour, the trigger that causes it to tick,
and a dict of stat modifiers (positive = buff, negative = debuff).
"""
from __future__ import annotations
import random
from typing import Any

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

STATUS_REGISTRY: dict[str, dict[str, Any]] = {
    "fatigue": {
        "name": "Fatigue",
        "duration": 3,
        "trigger": "travel",
        "effects": {"ATK": -2, "DEX": -1},
        "description": "Exhaustion slows your reflexes and weakens strikes.",
    },
    "poison": {
        "name": "Poison",
        "duration": 3,
        "trigger": "combat_tick_player_start",
        "effects": {"ATK": -1, "CON": -2},
        "description": "Venom courses through your veins, sapping vitality.",
    },
    "bleed": {
        "name": "Bleed",
        "duration": 3,
        "trigger": "combat_tick_player_start",
        "effects": {"CON": -1},
        "description": "Open wounds refuse to clot — you lose blood each round.",
    },
    "stun": {
        "name": "Stun",
        "duration": 1,
        "trigger": "combat_tick_player_start",
        "effects": {"DEX": -5, "ATK": -5},
        "description": "Dazed and reeling — you can barely act.",
    },
    "weaken": {
        "name": "Weaken",
        "duration": 3,
        "trigger": "combat_tick_player_start",
        "effects": {"STR": -3, "ATK": -2},
        "description": "Muscles fail you; every swing is sluggish.",
    },
    "guard": {
        "name": "Guard",
        "duration": 1,
        "trigger": "combat_tick_player_start",
        "effects": {"AC": 2},
        "description": "Braced behind your shield — incoming blows glance off.",
    },
    "covered": {
        "name": "Covered",
        "duration": 2,
        "trigger": "combat_tick_player_start",
        "effects": {"AC": 3},
        "description": "Taking cover behind solid ground grants excellent protection.",
    },
    "high_ground": {
        "name": "High Ground",
        "duration": 2,
        "trigger": "combat_tick_player_start",
        "effects": {"ATK": 2},
        "description": "Elevation advantage — your strikes rain down harder.",
    },
    "well_rested": {
        "name": "Well Rested",
        "duration": 1,
        "trigger": "combat",
        "effects": {"ATK": 1, "CON": 1, "DEX": 1},
        "description": "A good night's sleep sharpens body and mind.",
    },
    "sheltered": {
        "name": "Sheltered",
        "duration": 1,
        "trigger": "travel",
        "effects": {},
        "description": "Protected from the elements; no weather penalties.",
    },
    "dying": {
        "name": "Dying",
        "duration": -1,  # indefinite until removed
        "trigger": "combat_tick_player_start",
        "effects": {"ATK": -10, "DEX": -10, "STR": -10},
        "description": "Collapsed on the ground, clinging to the last thread of life.",
    },
    "wounded": {
        "name": "Wounded",
        "duration": 5,
        "trigger": "travel",
        "effects": {"ATK": -1, "CON": -1},
        "description": "Lingering injuries slow you down outside of combat.",
    },
}

# ---------------------------------------------------------------------------
# Active-status helpers — statuses live under state["statuses"]
# Each entry: {name, remaining, trigger, effects}
# ---------------------------------------------------------------------------


def _ensure_statuses(state: dict) -> list[dict]:
    state.setdefault("statuses", [])
    return state["statuses"]


def apply_status(state: dict, status_name: str, duration: int | None = None) -> bool:
    """Apply *status_name* to *state*. Returns True if applied, False if unknown or already active."""
    entry = STATUS_REGISTRY.get(status_name)
    if entry is None:
        return False
    statuses = _ensure_statuses(state)
    # Don't stack: refresh duration instead
    for s in statuses:
        if s["name"] == status_name:
            if duration is not None:
                s["remaining"] = duration
            return True
    dur = duration if duration is not None else entry["duration"]
    statuses.append({
        "name": status_name,
        "remaining": dur,
        "trigger": entry["trigger"],
        "effects": dict(entry["effects"]),
    })
    return True


def remove_status(state: dict, status_name: str) -> bool:
    """Remove *status_name* from state. Returns True if it was present."""
    statuses = _ensure_statuses(state)
    before = len(statuses)
    state["statuses"] = [s for s in statuses if s["name"] != status_name]
    return len(state["statuses"]) < before


def has_status(state: dict, status_name: str) -> bool:
    return any(s["name"] == status_name for s in _ensure_statuses(state))


def clear_statuses_by_trigger(state: dict, trigger: str) -> list[str]:
    """Remove all statuses whose trigger matches; return list of removed names."""
    statuses = _ensure_statuses(state)
    removed = [s["name"] for s in statuses if s["trigger"] == trigger]
    state["statuses"] = [s for s in statuses if s["trigger"] != trigger]
    return removed


def get_active_modifiers(state: dict) -> dict:
    """Aggregate stat modifiers from every active status."""
    mods: dict[str, int] = {}
    for s in _ensure_statuses(state):
        for stat, val in s.get("effects", {}).items():
            mods[stat] = mods.get(stat, 0) + val
    return mods


def tick_statuses(state: dict, trigger: str, rng: random.Random | None = None) -> list[str]:
    """Tick durations for statuses matching *trigger*. Returns names of expired & removed statuses."""
    statuses = _ensure_statuses(state)
    expired: list[str] = []
    surviving: list[dict] = []
    for s in statuses:
        if s["trigger"] != trigger:
            surviving.append(s)
            continue
        rem = s["remaining"]
        if rem < 0:
            # indefinite
            surviving.append(s)
        elif rem == 1:
            expired.append(s["name"])
            # don't keep — expired
        else:
            s["remaining"] = rem - 1
            surviving.append(s)
    state["statuses"] = surviving
    return expired


def is_dying(state: dict) -> bool:
    return has_status(state, "dying")


def is_stunned(state: dict) -> bool:
    return has_status(state, "stun")
