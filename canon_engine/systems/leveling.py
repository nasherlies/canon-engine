"""XP, levels, stat spend, leveling formula."""

from __future__ import annotations

from typing import Any

from canon_engine.systems.character import xp_to_next, level_up


def grant_xp(state: dict[str, Any], amount: int) -> dict[str, Any]:
    char = state.setdefault("character", {})
    char["xp"] = char.get("xp", 0) + amount
    return {"xp_gained": amount, "total_xp": char["xp"], "xp_to_next": xp_to_next(char.get("level", 1))}


def try_level_up(state: dict[str, Any]) -> dict[str, Any]:
    return level_up(state)


def spend_stat_point(state: dict[str, Any], stat: str) -> dict[str, Any]:
    char = state.get("character", state)
    pts = char.get("stat_points", 0)
    if pts <= 0:
        return {"success": False, "reason": "No stat points available."}
    stats = char.get("stats", {})
    if stat not in stats:
        return {"success": False, "reason": f"Unknown stat: {stat}"}
    stats[stat] += 1
    char["stat_points"] = pts - 1
    return {"success": True, "stat": stat, "new_value": stats[stat]}
