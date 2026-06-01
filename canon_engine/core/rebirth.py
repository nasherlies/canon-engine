"""Canon Engine — Rebirth System

Rebirth paths after death: standard, ascension, or descension.
"""
from __future__ import annotations

import random
from typing import Any

from canon_engine.core.stats import STAT_KEYS

# ---------------------------------------------------------------------------
# Rebirth paths
# ---------------------------------------------------------------------------

REBIRTH_PATHS = {
    "standard": {
        "name": "Standard Rebirth",
        "description": "Return to life with some losses. The familiar path.",
        "gold_loss_pct": 0.5,
        "stat_penalty": True,
        "xp_bonus": 0,
        "world_difficulty_increase": False,
        "chaos_change": 0,
    },
    "ascension": {
        "name": "Ascension",
        "description": "Keep your power, but the world grows harder around you.",
        "gold_loss_pct": 0.0,
        "stat_penalty": False,
        "xp_bonus": 200,
        "world_difficulty_increase": True,
        "chaos_change": 0,
    },
    "descension": {
        "name": "Descension",
        "description": "Dark powers restore you with a terrible bargain.",
        "gold_loss_pct": 0.0,
        "stat_penalty": False,
        "xp_bonus": 100,
        "world_difficulty_increase": False,
        "chaos_change": 10,
    },
}


def resolve_rebirth(
    state: dict[str, Any],
    path: str,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Resolve a rebirth along the chosen path.

    Parameters
    ----------
    state : dict
        Game state.
    path : str
        One of 'standard', 'ascension', 'descension'.
    rng : random.Random, optional
        RNG source.

    Returns
    -------
    dict
        {ok, path, message, consequences}.
    """
    _rng = rng or random.Random()

    if path not in REBIRTH_PATHS:
        return {"ok": False, "message": f"Unknown rebirth path: {path}. Choose: {', '.join(REBIRTH_PATHS)}"}

    info = REBIRTH_PATHS[path]
    consequences: dict[str, Any] = {
        "gold_lost": 0,
        "stat_penalized": None,
        "xp_gained": 0,
        "world_harder": False,
        "chaos_change": 0,
    }

    # Gold loss
    if info["gold_loss_pct"] > 0:
        gold = state.get("gold", 0)
        lost = int(gold * info["gold_loss_pct"])
        state["gold"] = gold - lost
        consequences["gold_lost"] = lost

    # Stat penalty (random stat -1)
    if info["stat_penalty"]:
        stats = state.get("stats", {})
        stat_key = _rng.choice(STAT_KEYS)
        old_val = stats.get(stat_key, 10)
        stats[stat_key] = max(1, old_val - 1)
        consequences["stat_penalized"] = {"stat": stat_key, "old": old_val, "new": stats[stat_key]}

    # XP bonus
    if info["xp_bonus"] > 0:
        state["xp"] = state.get("xp", 0) + info["xp_bonus"]
        consequences["xp_gained"] = info["xp_bonus"]

    # World difficulty
    if info["world_difficulty_increase"]:
        wf = state.setdefault("world_flags", {})
        wf["difficulty_level"] = wf.get("difficulty_level", 0) + 1
        consequences["world_harder"] = True

    # Chaos change
    if info["chaos_change"] != 0:
        state["chaos_score"] = state.get("chaos_score", 0) + info["chaos_change"]
        consequences["chaos_change"] = info["chaos_change"]

    # Build message
    parts = [f"**{info['name']}** — {info['description']}"]
    if consequences["gold_lost"] > 0:
        parts.append(f"Lost {consequences['gold_lost']} gold.")
    if consequences["stat_penalized"]:
        sp = consequences["stat_penalized"]
        parts.append(f"{sp['stat']} decreased: {sp['old']} → {sp['new']}.")
    if consequences["xp_gained"] > 0:
        parts.append(f"Gained {consequences['xp_gained']} bonus XP.")
    if consequences["world_harder"]:
        parts.append("The world grows more dangerous...")
    if consequences["chaos_change"] > 0:
        parts.append(f"Chaos score +{consequences['chaos_change']}.")

    return {
        "ok": True,
        "path": path,
        "message": " ".join(parts),
        "consequences": consequences,
    }


def apply_rebirth_consequences(
    state: dict[str, Any],
    rebirth_result: dict[str, Any],
) -> None:
    """Apply rebirth consequences to the game state.

    Sets alive, restores HP, clears death/dying status,
    and moves player to last rest location.
    """
    # Revive
    state["alive"] = True
    state["hp"] = state.get("max_hp", 100)

    # Clear death-related status
    statuses = state.get("statuses", [])
    state["statuses"] = [s for s in statuses if s.get("name") not in ("dying", "dead")]
    state.pop("death_saves", None)

    # Exit underworld if present
    if state.get("underworld", {}).get("active"):
        state["underworld"] = {"active": False, "soul": None}

    # Move to last rest location
    last_rest = state.get("last_rest_location", state.get("world", {}).get("location", "Unknown"))
    if "world" in state:
        state["world"]["location"] = last_rest

    # Record in fallen heroes log
    state.setdefault("fallen_heroes", []).append({
        "name": state.get("player", {}).get("name", state.get("name", "Unknown")),
        "turn": state.get("turn", 0),
        "rebirth_path": rebirth_result.get("path", "unknown"),
    })
