"""Faction standing, reputation tiers."""

from __future__ import annotations

from typing import Any

REPUTATION_TIERS = [
    (-100, -80, "Hated"),
    (-79, -40, "Hostile"),
    (-39, -10, "Unfriendly"),
    (-9, 9, "Neutral"),
    (10, 39, "Friendly"),
    (40, 79, "Honored"),
    (80, 100, "Revered"),
]


def get_factions(state: dict[str, Any]) -> dict[str, int]:
    return state.setdefault("factions", {})


def get_standing(faction_rep: int) -> str:
    for lo, hi, label in REPUTATION_TIERS:
        if lo <= faction_rep <= hi:
            return label
    return "Neutral"


def adjust_reputation(state: dict[str, Any], faction: str, delta: int) -> dict[str, Any]:
    f = get_factions(state)
    f[faction] = max(-100, min(100, f.get(faction, 0) + delta))
    return {"faction": faction, "reputation": f[faction], "standing": get_standing(f[faction])}
