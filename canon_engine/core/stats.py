"""Stats module – stat modifiers, HP/MP calculation, encumbrance, luck."""

from __future__ import annotations

import math


STAT_KEYS = ["STR", "DEX", "INT", "CHA", "CON", "LCK"]


def get_stat_modifier(value: int) -> int:
    """D&D-style modifier: (value - 10) // 2."""
    return (value - 10) // 2


def calculate_max_hp(player: dict) -> int:
    """50 + CON * 5."""
    con = player.get("stats", {}).get("CON", 10)
    return 50 + con * 5


def calculate_max_mp(player: dict) -> int:
    """30 + INT * 3."""
    intel = player.get("stats", {}).get("INT", 10)
    return 30 + intel * 3


def nap_heal_amount(player: dict) -> int:
    """15% of hp_max, minimum 1."""
    hp_max = player.get("hp_max") or calculate_max_hp(player)
    return max(1, math.floor(hp_max * 0.15))


def sleep_heal_amount(player: dict) -> int:
    """Full heal to hp_max (returns hp_max, caller sets hp = hp_max)."""
    return player.get("hp_max") or calculate_max_hp(player)


def get_encumbrance_modifier(carry: float, cap: float) -> int:
    """0 if under cap, -2 to -6 penalty when over cap.

    Every 25% over cap adds another -2.
    """
    if carry <= cap:
        return 0
    over_ratio = (carry - cap) / cap if cap > 0 else 1.0
    steps = min(3, math.ceil(over_ratio / 0.25))
    return -2 * steps


def get_luck_table_modifier(luck_mod: int) -> int:
    """Small bonus/penalty from luck modifier.

    -2 or worse → -1
    -1 → 0
    0 → 0
    +1 to +2 → +1
    +3 to +4 → +2
    +5 or more → +3
    """
    if luck_mod <= -2:
        return -1
    if luck_mod <= 0:
        return 0
    if luck_mod <= 2:
        return 1
    if luck_mod <= 4:
        return 2
    return 3
