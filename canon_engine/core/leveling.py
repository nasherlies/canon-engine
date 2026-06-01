"""
Canon Engine — Leveling System

XP tracking, level-up logic, and turn-based XP grants.
"""

from __future__ import annotations

from typing import Any

from canon_engine.core.stats import STAT_KEYS, calculate_max_hp, calculate_max_mp

# ───────────────────────────────────────────────────────────────────
# Constants
# ───────────────────────────────────────────────────────────────────
XP_FLOOR_PER_TURN: int = 5

# XP required to level up scales: level × 100
def _xp_for_level(level: int) -> int:
    """Return XP threshold for the next level-up."""
    return level * 100


# ═══════════════════════════════════════════════════════════════════
# XP management
# ═══════════════════════════════════════════════════════════════════

def add_xp(state: dict[str, Any], amount: int) -> dict[str, Any]:
    """
    Add XP to the character.  Returns a result dict.

    Keys: ok, message, xp_added, xp, xp_needed, level, levelled_up
    """
    state.setdefault("xp", 0)
    state.setdefault("level", 1)

    state["xp"] += amount

    xp_needed = _xp_for_level(state["level"])
    levelled = False

    # Check for level-up
    if state["xp"] >= xp_needed:
        levelled = True
        state["xp"] -= xp_needed
        state["level"] += 1
        state["stat_points"] = state.get("stat_points", 0) + 3
        # Recalculate HP/MP
        stats = state.get("stats", {})
        player_proxy = {"stats": stats, "level": state["level"]}; state["max_hp"] = calculate_max_hp(player_proxy)
        state["max_mp"] = calculate_max_mp(player_proxy)
        state["hp"] = state["max_hp"]
        state["mp"] = state["max_mp"]

    return {
        "ok": True,
        "message": f"Gained **{amount}** XP.",
        "xp_added": amount,
        "xp": state["xp"],
        "xp_needed": _xp_for_level(state["level"]),
        "level": state["level"],
        "levelled_up": levelled,
    }


def apply_level_up(state: dict[str, Any]) -> dict[str, Any]:
    """
    Apply a pending level-up: +3 stat_points, increment level, reset XP.

    Usually called when the player confirms a level-up.
    """
    state.setdefault("stat_points", 0)
    state["stat_points"] += 3
    state.setdefault("level", 1)
    state["level"] += 1
    state["xp"] = 0

    # Recalculate HP/MP
    stats = state.get("stats", {})
    player_proxy = {"stats": stats, "level": state["level"]}; state["max_hp"] = calculate_max_hp(player_proxy)
    state["max_mp"] = calculate_max_mp(player_proxy)
    state["hp"] = state["max_hp"]
    state["mp"] = state["max_mp"]

    return {
        "ok": True,
        "message": f"Level up! Now level **{state['level']}**. +3 stat points (total: {state['stat_points']}).",
        "level": state["level"],
        "stat_points": state["stat_points"],
    }


def format_levelup_display(state: dict[str, Any]) -> str:
    """
    Format a level-up summary for display.
    """
    level = state.get("level", 1)
    sp = state.get("stat_points", 0)
    xp = state.get("xp", 0)
    xp_needed = _xp_for_level(level)

    lines = [
        f"✦ LEVEL {level} ✦",
        f"  Stat Points: {sp}",
        f"  XP: {xp} / {xp_needed}",
        "",
        "  Stats:",
    ]
    stats = state.get("stats", {})
    for key in STAT_KEYS:
        val = stats.get(key, 10)
        mod = (val - 10) // 2
        sign = "+" if mod >= 0 else ""
        lines.append(f"    {key}: {val} ({sign}{mod})")

    return "\n".join(lines)


def grant_turn_xp(state: dict[str, Any], command_kind: str) -> dict[str, Any] | None:
    """
    Grant floor XP for active roleplay commands (/do, /say, etc.).

    Returns the add_xp result dict, or None if no XP granted.
    """
    xp_kinds = {"say", "do", "think", "talk", "attack", "interact", "travel"}
    if command_kind not in xp_kinds:
        return None

    return add_xp(state, XP_FLOOR_PER_TURN)
