"""Canon Engine — Party Combat System

Companions fight alongside the player during combat.
Each companion acts on the party turn based on orders or default AI.
"""
from __future__ import annotations

import random
from typing import Any

from .combat_math import d20, roll_dice, render_hp_bar
from .stats import get_stat_modifier


# ---------------------------------------------------------------------------
# Party building
# ---------------------------------------------------------------------------


def build_combat_party(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Build party list from state['companions'] where recruited=True and alive.

    Returns a list of companion dicts ready for combat (with combat_hp, etc.).
    """
    companions = state.get("companions", [])
    party = []
    for c in companions:
        if not c.get("recruited", False):
            continue
        if not c.get("alive", True):
            continue
        # Build combat-ready copy
        stats = c.get("stats", {})
        hp = c.get("hp", c.get("max_hp", 30))
        max_hp = c.get("max_hp", 30)
        combat_comp = {
            "name": c.get("name", "Companion"),
            "hp": hp,
            "max_hp": max_hp,
            "ac": c.get("ac", 10 + get_stat_modifier(stats.get("DEX", 10))),
            "attack_mod": c.get("attack_mod", get_stat_modifier(stats.get("STR", 10))),
            "damage": c.get("damage", (1, 6)),
            "stat_mod": get_stat_modifier(stats.get("STR", 10)),
            "stats": stats,
            "loyalty": c.get("loyalty", 50),
            "order": c.get("order", None),
            "original_ref": c,
        }
        party.append(combat_comp)
    return party


# ---------------------------------------------------------------------------
# Companion attack
# ---------------------------------------------------------------------------


def companion_attack(
    companion: dict[str, Any],
    enemy: dict[str, Any],
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Roll a companion attack: d20 + companion_stat_mod vs enemy AC.

    Returns dict with: roll, natural, total, hit, crit, fumble, damage.
    """
    _rng = rng or random
    natural = d20(_rng)
    stat_mod = companion.get("attack_mod", companion.get("stat_mod", 0))
    total = natural + stat_mod
    enemy_ac = enemy.get("ac", 10)
    is_crit = natural == 20
    is_fumble = natural == 1
    hit = is_crit or (not is_fumble and total >= enemy_ac)

    dmg = 0
    if hit:
        base_dice = companion.get("damage", (1, 6))
        n, sides = base_dice
        if is_crit:
            n *= 2
        dmg = max(0, sum(_rng.randint(1, sides) for _ in range(n)) + companion.get("stat_mod", 0))

    return {
        "roll": total,
        "natural": natural,
        "total": total,
        "hit": hit,
        "crit": is_crit,
        "fumble": is_fumble,
        "damage": dmg,
    }


# ---------------------------------------------------------------------------
# Loyalty check
# ---------------------------------------------------------------------------


def roll_companion_loyalty(
    companion: dict[str, Any],
    action: str,
    rng: random.Random | None = None,
) -> bool:
    """Loyalty check for obedience. Returns True if companion obeys.

    Threshold: loyalty / 100.  Random [0,1) < threshold → obey.
    Negative loyalty always fails.
    """
    _rng = rng or random
    loyalty = companion.get("loyalty", 50)
    if loyalty <= 0:
        return False
    threshold = loyalty / 100.0
    return _rng.random() < threshold


# ---------------------------------------------------------------------------
# Combo damage
# ---------------------------------------------------------------------------


def resolve_combo_damage(
    state: dict[str, Any],
    companion: dict[str, Any],
    enemy: dict[str, Any],
    rng: random.Random | None = None,
) -> int:
    """Bonus damage when companion attacks same foe as player.

    50% of companion base damage (rounded down, min 0).
    """
    _rng = rng or random
    base_dice = companion.get("damage", (1, 6))
    n, sides = base_dice
    base_dmg = sum(_rng.randint(1, sides) for _ in range(n))
    return max(0, base_dmg // 2)


# ---------------------------------------------------------------------------
# Party turn resolution
# ---------------------------------------------------------------------------


def resolve_party_turn(
    state: dict[str, Any],
    player_target: dict[str, Any] | None,
    rng: random.Random | None = None,
) -> list[str]:
    """Each companion acts based on /order or default behavior.

    Default: attack if HP > 30%, block if HP < 30%.
    Ordered: attack/block/item/flee as specified.

    Returns list of narration strings describing each companion's action.
    """
    _rng = rng or random
    party = build_combat_party(state)
    log: list[str] = []

    for comp in party:
        # Loyalty check
        order = comp.get("order")
        action = order if order else "auto"

        if not roll_companion_loyalty(comp, action, _rng):
            log.append(f"{comp['name']} hesitates, refusing orders!")
            continue

        # Determine action
        if order in ("attack", "block", "item", "flee"):
            chosen = order
        else:
            # Default AI
            hp_pct = comp["hp"] / max(1, comp["max_hp"])
            chosen = "attack" if hp_pct > 0.30 else "block"

        if chosen == "attack" and player_target and player_target.get("alive", True):
            result = companion_attack(comp, player_target, _rng)
            if result["crit"]:
                log.append(f"{comp['name']} lands a CRITICAL hit for {result['damage']} damage!")
            elif result["hit"]:
                log.append(f"{comp['name']} strikes {player_target.get('display_name', 'enemy')} for {result['damage']} damage.")
            else:
                log.append(f"{comp['name']} misses.")
            if result["hit"]:
                player_target["hp"] = max(0, player_target.get("hp", 0) - result["damage"])
                if player_target["hp"] <= 0:
                    player_target["alive"] = False
        elif chosen == "block":
            log.append(f"{comp['name']} raises their guard.")
            comp["blocking"] = True
        elif chosen == "item":
            log.append(f"{comp['name']} uses an item.")
        elif chosen == "flee":
            log.append(f"{comp['name']} retreats!")
        else:
            log.append(f"{comp['name']} holds position.")

    return log


# ---------------------------------------------------------------------------
# Sync vitals back
# ---------------------------------------------------------------------------


def sync_companion_vitals(state: dict[str, Any]) -> None:
    """After combat, sync HP changes back to the companions list."""
    companions = state.get("companions", [])
    for c in companions:
        if not c.get("recruited", False):
            continue
        # If companion has combat_hp, sync it back
        if "combat_hp" in c:
            c["hp"] = c["combat_hp"]
            del c["combat_hp"]
        # Ensure alive flag
        if c.get("hp", 0) <= 0:
            c["alive"] = False
            c["hp"] = 0


# ---------------------------------------------------------------------------
# Format party status
# ---------------------------------------------------------------------------


def format_party_status(party: list[dict[str, Any]]) -> str:
    """Render HP bars for each companion in the party."""
    if not party:
        return "No companions in party."
    lines = ["**Party Status:**"]
    for comp in party:
        hp = comp.get("hp", 0)
        max_hp = comp.get("max_hp", 1)
        bar = render_hp_bar(hp, max_hp, width=12)
        lines.append(f"  {comp['name']}: [{bar}] {hp}/{max_hp}")
    return "\n".join(lines)
