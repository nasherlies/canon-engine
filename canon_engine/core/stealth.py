"""Canon Engine — Stealth & Scouting System

Stealth, scouting, detection, and trap mechanics.
"""
from __future__ import annotations

import random
from typing import Any

from .combat_math import d20
from .stats import get_stat_modifier
from .status import apply_status, has_status, remove_status


# ---------------------------------------------------------------------------
# Trap registry
# ---------------------------------------------------------------------------


TRAPS: dict[str, dict[str, Any]] = {
    "tripwire": {
        "dc": 10,
        "damage": (1, 6),
        "element": "physical",
    },
    "pit_trap": {
        "dc": 12,
        "damage": (2, 6),
        "element": "physical",
    },
    "poison_dart": {
        "dc": 14,
        "damage": (1, 4),
        "element": "poison",
    },
    "fire_rune": {
        "dc": 15,
        "damage": (3, 6),
        "element": "fire",
    },
}


# ---------------------------------------------------------------------------
# Scout
# ---------------------------------------------------------------------------


def resolve_scout(
    state: dict[str, Any],
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Scout ahead.  DEX check vs location scout_dc (default 12).

    On success: reveals traps, enemies, loot, terrain features.
    On fail: nothing found.
    """
    _rng = rng or random
    world = state.get("world", {})
    flags = state.get("world_flags", {})
    dc = world.get("scout_dc", flags.get("scout_dc", 12))

    dex_mod = get_stat_modifier(state.get("stats", {}).get("DEX", 10))
    roll = d20(_rng)
    total = roll + dex_mod
    success = roll == 20 or (roll != 1 and total >= dc)

    if success:
        reveals: dict[str, Any] = {}
        # Reveal traps
        location_traps = flags.get("traps", world.get("traps", []))
        if location_traps:
            reveals["traps"] = location_traps if isinstance(location_traps, list) else [location_traps]
        # Reveal enemies
        location_enemies = flags.get("enemies", world.get("enemies", []))
        if location_enemies:
            reveals["enemies"] = location_enemies if isinstance(location_enemies, list) else [location_enemies]
        # Reveal loot
        location_loot = flags.get("loot", world.get("loot", []))
        if location_loot:
            reveals["loot"] = location_loot if isinstance(location_loot, list) else [location_loot]
        # Reveal terrain features
        terrain_feats = world.get("terrain_features", flags.get("terrain", {}))
        if terrain_feats:
            reveals["terrain_features"] = terrain_feats

        return {
            "success": True,
            "roll": roll,
            "total": total,
            "dc": dc,
            "reveals": reveals,
            "narration": f"Scouting succeeds! (rolled {total} vs DC {dc})",
        }

    return {
        "success": False,
        "roll": roll,
        "total": total,
        "dc": dc,
        "reveals": {},
        "narration": f"Scouting finds nothing. (rolled {total} vs DC {dc})",
    }


# ---------------------------------------------------------------------------
# Stealth
# ---------------------------------------------------------------------------


def resolve_stealth(
    state: dict[str, Any],
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Enter stealth mode.  DEX check DC varies by environment.

    Lit areas: DC +5.  On fail: status applied briefly (exposed).
    """
    _rng = rng or random
    world = state.get("world", {})
    flags = state.get("world_flags", {})

    base_dc = flags.get("stealth_dc", 12)
    lit = world.get("lit", flags.get("lit", False))
    dc = base_dc + (5 if lit else 0)

    dex_mod = get_stat_modifier(state.get("stats", {}).get("DEX", 10))
    roll = d20(_rng)
    total = roll + dex_mod
    success = roll == 20 or (roll != 1 and total >= dc)

    if success:
        state.setdefault("world_flags", {})
        state["world_flags"]["stealth"] = True
        return {
            "success": True,
            "roll": roll,
            "total": total,
            "dc": dc,
            "narration": f"You slip into the shadows. (rolled {total} vs DC {dc})",
        }
    else:
        # Apply brief exposed status (not in STATUS_REGISTRY, apply manually)
        state.setdefault("statuses", []).append({
            "name": "exposed",
            "remaining": 1,
            "trigger": "combat_tick_player_start",
            "effects": {"DEX": -2},
        })
        return {
            "success": False,
            "roll": roll,
            "total": total,
            "dc": dc,
            "narration": f"You stumble and are spotted! (rolled {total} vs DC {dc})",
        }


# ---------------------------------------------------------------------------
# Detect
# ---------------------------------------------------------------------------


def resolve_detect(
    state: dict[str, Any],
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Detect hidden enemies/traps.  WIS/INT check (best of).

    DC defaults to 13.
    """
    _rng = rng or random
    flags = state.get("world_flags", {})
    dc = flags.get("detect_dc", 13)

    stats = state.get("stats", {})
    wis_mod = get_stat_modifier(stats.get("WIS", 10))
    int_mod = get_stat_modifier(stats.get("INT", 10))
    best_mod = max(wis_mod, int_mod)

    roll = d20(_rng)
    total = roll + best_mod
    success = roll == 20 or (roll != 1 and total >= dc)

    detected: dict[str, Any] = {}
    if success:
        # Reveal hidden threats
        hidden_enemies = flags.get("hidden_enemies", [])
        if hidden_enemies:
            detected["hidden_enemies"] = hidden_enemies
        hidden_traps = flags.get("hidden_traps", [])
        if hidden_traps:
            detected["hidden_traps"] = hidden_traps
        if not detected:
            detected["area_clear"] = True

    return {
        "success": success,
        "roll": roll,
        "total": total,
        "dc": dc,
        "detected": detected,
        "narration": (
            f"You scan the area carefully. (rolled {total} vs DC {dc})"
            if success
            else f"You notice nothing unusual. (rolled {total} vs DC {dc})"
        ),
    }


# ---------------------------------------------------------------------------
# Disarm
# ---------------------------------------------------------------------------


def resolve_disarm(
    state: dict[str, Any],
    trap_name: str,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Disarm a trap.  DEX check, DC varies by trap type.

    Returns dict with: success, roll, dc, trap, narration.
    """
    _rng = rng or random
    trap = TRAPS.get(trap_name)
    if trap is None:
        return {
            "success": False,
            "trap": trap_name,
            "narration": f"Unknown trap type: '{trap_name}'.",
        }

    dc = trap["dc"]
    dex_mod = get_stat_modifier(state.get("stats", {}).get("DEX", 10))
    roll = d20(_rng)
    total = roll + dex_mod
    success = roll == 20 or (roll != 1 and total >= dc)

    if success:
        return {
            "success": True,
            "roll": roll,
            "total": total,
            "dc": dc,
            "trap": trap_name,
            "narration": f"You carefully disarm the {trap_name.replace('_', ' ')}. (rolled {total} vs DC {dc})",
        }
    else:
        # Trigger the trap damage
        dmg_range = trap["damage"]
        damage = _rng.randint(dmg_range[0], dmg_range[1])
        element = trap["element"]
        return {
            "success": False,
            "roll": roll,
            "total": total,
            "dc": dc,
            "trap": trap_name,
            "damage": damage,
            "element": element,
            "narration": f"The {trap_name.replace('_', ' ')} triggers! You take {damage} {element} damage. (rolled {total} vs DC {dc})",
        }


# ---------------------------------------------------------------------------
# Travel trap hook
# ---------------------------------------------------------------------------


def travel_trap_hook(
    state: dict[str, Any],
    rng: random.Random | None = None,
) -> list[str]:
    """Check for traps when traveling.  Returns list of trap narration strings."""
    _rng = rng or random
    flags = state.get("world_flags", {})
    world = state.get("world", {})

    # Get traps at current location
    location_traps = flags.get("traps", world.get("traps", []))
    if not location_traps:
        return []

    messages: list[str] = []
    trap_list = location_traps if isinstance(location_traps, list) else [location_traps]

    for trap_info in trap_list:
        trap_name = trap_info if isinstance(trap_info, str) else trap_info.get("type", "tripwire")
        trap = TRAPS.get(trap_name, TRAPS["tripwire"])

        # Passive detection: WIS check vs trap DC
        stats = state.get("stats", {})
        wis_mod = get_stat_modifier(stats.get("WIS", 10))
        roll = d20(_rng)
        total = roll + wis_mod
        dc = trap["dc"]

        if roll == 20 or (roll != 1 and total >= dc):
            messages.append(f"You spot a {trap_name.replace('_', ' ')} and avoid it!")
        else:
            # Trigger trap
            dmg_range = trap["damage"]
            damage = _rng.randint(dmg_range[0], dmg_range[1])
            element = trap["element"]
            messages.append(f"You walk into a {trap_name.replace('_', ' ')}! {damage} {element} damage.")

    return messages


# ---------------------------------------------------------------------------
# Stealth surprise
# ---------------------------------------------------------------------------


def stealth_surprise_next_attack(state: dict[str, Any]) -> bool:
    """Consume stealth for a surprise round.  Returns True if stealth was active.

    Removes stealth flag after consumption.
    """
    flags = state.get("world_flags", {})
    if flags.get("stealth", False):
        flags["stealth"] = False
        flags["surprise_attack"] = True
        return True
    return False


def break_stealth(state: dict[str, Any], reason: str) -> None:
    """Remove stealth status from the player."""
    flags = state.get("world_flags", {})
    if flags.get("stealth", False):
        flags["stealth"] = False
        flags["stealth_break_reason"] = reason
