"""Turn-based combat with free functions on plain dict (NOT a class).

state['combat'] blob:
    active: bool
    enemies: list[dict]  — each has name, hp, max_hp, ac, attack_bonus, damage_dice
    active_enemy_index: int
    round: int
    turn: str  — 'player' | 'enemy'
"""

from __future__ import annotations

import random
from typing import Any


def get_combat(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault("combat", {
        "active": False, "enemies": [], "active_enemy_index": 0,
        "round": 0, "turn": "player",
    })


def start_combat(state: dict[str, Any], enemies: list[dict[str, Any]]) -> None:
    c = get_combat(state)
    c["active"] = True
    c["enemies"] = enemies
    c["active_enemy_index"] = 0
    c["round"] = 1
    c["turn"] = "player"


def _d20() -> int:
    return random.randint(1, 20)


def _roll_dice(expr: str) -> int:
    """Parse 'NdM+K' and roll.  Fallback: return int(expr) or 0."""
    try:
        if "d" in expr:
            parts = expr.replace("-", "+-").split("+")
            total = 0
            for p in parts:
                p = p.strip()
                if "d" in p:
                    n, m = p.split("d", 1)
                    total += sum(random.randint(1, int(m)) for _ in range(int(n or 1)))
                elif p:
                    total += int(p)
            return max(0, total)
        return max(0, int(expr))
    except Exception:
        return 4


# ---------------------------------------------------------------------------
# Player actions
# ---------------------------------------------------------------------------

def resolve_player_attack(state: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    """Player attacks the active enemy."""
    c = get_combat(state)
    if not c["active"] or not c["enemies"]:
        return {"narration": "There's nothing to attack."}
    enemy = c["enemies"][c["active_enemy_index"]]
    char = state.get("character", state)
    roll = _d20()
    total = roll + char.get("proficiency_bonus", 2)
    if total < enemy.get("ac", 10):
        return {"narration": f"You swing at {enemy['name']} but miss! (rolled {roll})"}
    dmg = _roll_dice(parsed.get("damage_dice", "1d8"))
    enemy["hp"] = max(0, enemy["hp"] - dmg)
    narration = f"You strike {enemy['name']} for {dmg} damage!"
    if enemy["hp"] <= 0:
        narration += f" {enemy['name']} is defeated!"
        _advance_enemy(c)
    # Enemy turn
    enemy_result = _do_enemy_turn(state)
    narration += "\n" + enemy_result.get("narration", "")
    return {"narration": narration}


def resolve_player_block(state: dict[str, Any]) -> dict[str, Any]:
    """Player blocks, gaining temp AC for the enemy turn."""
    char = state.get("character", state)
    char["_blocking"] = True
    enemy_result = _do_enemy_turn(state)
    char.pop("_blocking", None)
    return {"narration": "You raise your guard.\n" + enemy_result.get("narration", "")}


def resolve_combat_flee(state: dict[str, Any]) -> dict[str, Any]:
    """Attempt to flee combat."""
    roll = _d20()
    if roll >= 10:
        get_combat(state)["active"] = False
        return {"narration": f"You manage to flee! (rolled {roll})"}
    enemy_result = _do_enemy_turn(state)
    return {"narration": f"Failed to flee! (rolled {roll})\n" + enemy_result.get("narration", "")}


# ---------------------------------------------------------------------------
# Enemy turn
# ---------------------------------------------------------------------------

def enemy_turn_resolve(state: dict[str, Any]) -> dict[str, Any]:
    """Public wrapper for enemy turn."""
    return _do_enemy_turn(state)


def _do_enemy_turn(state: dict[str, Any]) -> dict[str, Any]:
    c = get_combat(state)
    if not c["active"] or not c["enemies"]:
        return {"narration": ""}
    enemy = c["enemies"][c["active_enemy_index"]]
    char = state.get("character", state)
    ac = char.get("ac", 10) + (3 if char.get("_blocking") else 0)
    roll = _d20()
    total = roll + enemy.get("attack_bonus", 2)
    if total < ac:
        return {"narration": f"{enemy['name']} attacks but misses! (rolled {roll})"}
    dmg = _roll_dice(enemy.get("damage_dice", "1d6"))
    from canon_engine.systems.character import apply_damage
    apply_damage(state, dmg)
    return {"narration": f"{enemy['name']} hits you for {dmg} damage!"}


def _advance_enemy(c: dict[str, Any]) -> None:
    """Move to next enemy or end combat."""
    c["enemies"] = [e for e in c["enemies"] if e.get("hp", 0) > 0]
    if not c["enemies"]:
        c["active"] = False
    else:
        c["active_enemy_index"] = min(c["active_enemy_index"], len(c["enemies"]) - 1)
