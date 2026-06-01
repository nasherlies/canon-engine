"""Canon Engine — Combat System

D&D 2014 SRD rules: initiative, attack rolls, damage, crits, fumbles,
multi-enemy auto-numbering, status ticks, loot/XP rewards, and a combat
shell that only accepts /attack, /block, /item, /flee, /turn, /look,
/help, save, load.
"""
from __future__ import annotations
import random
from typing import Any

from .combat_math import (
    d20,
    roll_dice,
    attack_roll,
    damage_roll,
    ac_calc,
    proficiency_bonus,
    render_hp_bar,
    saving_throw,
)
from .enemy_ai import ENEMY_TYPES, resolve_enemy_turn
from .status import apply_status, has_status, tick_statuses, get_active_modifiers, is_dying, is_stunned, remove_status
from .elements import calculate_elemental_damage
from .stats import get_stat_modifier
from .rarity import roll_rarity

# ---------------------------------------------------------------------------
# Allowed commands during combat (for shell filtering)
# ---------------------------------------------------------------------------

COMBAT_ALLOWED_COMMANDS = frozenset({
    "attack", "block", "item", "flee", "turn", "look",
    "help", "save", "load", "look_enemies",
})

# ---------------------------------------------------------------------------
# Loot tables by rarity
# ---------------------------------------------------------------------------

_LOOT_BY_RARITY: dict[str, list[str]] = {
    "common": ["health_potion", "bandage", "torch", "ration", "rope"],
    "uncommon": ["greater_health_potion", "antidote", "silver_ring", "enchanted_cloth"],
    "rare": ["elixir_of_strength", "scroll_of_fireball", "mithril_shard"],
    "epic": ["amulet_of_vitality", "dragonscale_fragment"],
    "legendary": ["excalibur_shard", "phoenix_feather"],
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _auto_number_enemies(enemies: list[dict]) -> list[dict]:
    """Add display_name to enemies, numbering duplicates."""
    counts: dict[str, int] = {}
    for e in enemies:
        t = e.get("type", "enemy")
        counts[t] = counts.get(t, 0) + 1

    seen: dict[str, int] = {}
    for e in enemies:
        t = e.get("type", "enemy")
        seen[t] = seen.get(t, 0) + 1
        if counts[t] > 1:
            e["display_name"] = f"{t} {seen[t]}"
        else:
            e["display_name"] = t
    return enemies


def _build_enemy_instance(etype: str, rng: random.Random) -> dict:
    """Create a live enemy dict from ENEMY_TYPES."""
    template = ENEMY_TYPES.get(etype, ENEMY_TYPES["bandit"])
    hp_lo, hp_hi = template["hp_range"]
    hp = rng.randint(hp_lo, hp_hi)
    return {
        "type": etype,
        "display_name": etype,
        "hp": hp,
        "max_hp": hp,
        "ac": template["ac"],
        "attack_mod": template["attack_mod"],
        "damage": template["damage"],
        "damage_type": template.get("damage_type", "physical"),
        "abilities": [dict(a) for a in template.get("abilities", [])],
        "cooldowns": {},
        "resistances": template.get("resistances", {}),
        "xp": template.get("xp", 25),
        "gold": template.get("gold", (1, 5)),
        "loot_table": template.get("loot_table", []),
        "alive": True,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def start_combat(state: dict, encounter_data: dict, rng: random.Random | None = None) -> dict:
    """Begin combat: spawn up to 3 enemies, roll initiative, set combat state."""
    _rng = rng or random
    enemy_types = encounter_data.get("enemies", [])
    # Normalise — allow list of strings or list of dicts
    type_list: list[str] = []
    for e in enemy_types[:3]:
        if isinstance(e, str):
            type_list.append(e)
        elif isinstance(e, dict):
            type_list.append(e.get("type", "bandit"))

    enemies = [_build_enemy_instance(t, _rng) for t in type_list]
    enemies = _auto_number_enemies(enemies)

    # Initiative
    player_dex_mod = get_stat_modifier(state.get("stats", {}).get("DEX", 10))
    player_init = d20(_rng) + player_dex_mod
    enemy_inits = [(d20(_rng) + 0, i) for i, e in enumerate(enemies)]  # enemies use flat d20

    initiative_order: list[dict] = [{"type": "player", "initiative": player_init}]
    for init_val, idx in enemy_inits:
        initiative_order.append({"type": "enemy", "index": idx, "initiative": init_val})
    initiative_order.sort(key=lambda x: x["initiative"], reverse=True)

    state["combat"] = {
        "active": True,
        "enemies": enemies,
        "initiative": initiative_order,
        "round": 1,
        "player_moves_remaining": 1,
        "blocked": False,
        "victory": False,
        "defeat": False,
        "xp_total": 0,
        "loot": [],
        "gold_total": 0,
    }
    state["encounter_status"] = "combat"

    return {
        "status": "combat_started",
        "enemies": [e["display_name"] for e in enemies],
        "initiative": initiative_order,
        "round": 1,
        "moves_remaining": 1,
    }


def end_combat(state: dict, rng: random.Random | None = None) -> dict:
    """Conclude combat, compute XP/loot/gold rewards."""
    _rng = rng or random
    combat = state.get("combat", {})
    enemies = combat.get("enemies", [])

    xp_total = 0
    gold_total = 0
    loot: list[str] = []

    for e in enemies:
        if not e.get("alive", True):
            xp_total += e.get("xp", 25)
            gold_range = e.get("gold", (1, 5))
            if isinstance(gold_range, tuple):
                gold_total += _rng.randint(gold_range[0], gold_range[1])
            else:
                gold_total += gold_range
            # Roll loot
            rarity = roll_rarity(_rng)
            table = e.get("loot_table", _LOOT_BY_RARITY.get(rarity, []))
            if table:
                loot.append(_rng.choice(table))

    # Update player
    state.setdefault("xp", 0)
    state["xp"] += xp_total
    state.setdefault("gold", 0)
    state["gold"] += gold_total
    inv = state.setdefault("inventory", [])
    inv.extend(loot)

    # Cleanup combat state
    combat["active"] = False
    state["encounter_status"] = "none"
    state.pop("pending_encounter", None)

    return {
        "status": "combat_ended",
        "xp": xp_total,
        "gold": gold_total,
        "loot": loot,
    }


def resolve_attack(state: dict, target_index: int, rng: random.Random | None = None) -> dict:
    """Player attacks enemy at *target_index*."""
    _rng = rng or random
    combat = state.get("combat", {})
    enemies = combat.get("enemies", [])

    if target_index < 0 or target_index >= len(enemies):
        return {"status": "error", "description": "Invalid target."}

    target = enemies[target_index]
    if not target.get("alive", True):
        return {"status": "error", "description": f"{target['display_name']} is already defeated."}

    if is_stunned(state):
        return {"status": "stunned", "description": "You are stunned and cannot act!"}

    # Attack roll
    stats = state.get("stats", {})
    str_mod = get_stat_modifier(stats.get("STR", 10))
    dex_mod = get_stat_modifier(stats.get("DEX", 10))
    # Use STR for melee (default), DEX for finesse — simplified to STR
    ability_mod = str_mod
    prof = proficiency_bonus(state.get("level", 1))

    # Status modifiers
    mods = get_active_modifiers(state)
    atk_bonus = ability_mod + prof + mods.get("ATK", 0)

    total, is_crit, is_fumble = attack_roll(atk_bonus, 0, _rng)
    enemy_ac = target["ac"] + mods.get("AC_ENEMY_PENALTY", 0)

    combat["player_moves_remaining"] = max(0, combat.get("player_moves_remaining", 1) - 1)

    if is_fumble:
        return {
            "status": "fumble",
            "description": f"You fumble your attack against {target['display_name']}! Natural 1.",
            "target": target["display_name"],
            "roll": total,
        }

    hit = total >= enemy_ac or is_crit
    if not hit:
        return {
            "status": "miss",
            "description": f"You miss {target['display_name']}! (Rolled {total} vs AC {enemy_ac})",
            "target": target["display_name"],
            "roll": total,
        }

    # Damage
    weapon_die = (1, 8)  # default longsword
    base_dmg = damage_roll(weapon_die, ability_mod, is_crit, _rng)

    # Elemental — physical by default
    elem_result = calculate_elemental_damage(
        base_dmg, "physical", target.get("resistances", {}), state.get("world", {}).get("weather")
    )
    final_dmg = elem_result["final_damage"]

    target["hp"] = max(0, target["hp"] - final_dmg)
    if target["hp"] <= 0:
        target["alive"] = False

    crit_text = " **CRITICAL HIT!**" if is_crit else ""
    kill_text = f" {target['display_name']} is defeated!" if not target["alive"] else ""

    return {
        "status": "hit",
        "description": f"You strike {target['display_name']} for {final_dmg} damage!{crit_text}{kill_text}",
        "target": target["display_name"],
        "damage": final_dmg,
        "crit": is_crit,
        "remaining_hp": target["hp"],
        "killed": not target["alive"],
        "roll": total,
    }


def resolve_block(state: dict) -> dict:
    """Player blocks: +2 AC until next turn."""
    combat = state.get("combat", {})
    combat["blocked"] = True
    combat["player_moves_remaining"] = max(0, combat.get("player_moves_remaining", 1) - 1)
    apply_status(state, "guard", duration=1)
    return {
        "status": "block",
        "description": "You raise your guard! (+2 AC until your next turn)",
    }


def resolve_combat_item(state: dict, item_name: str, rng: random.Random | None = None) -> dict:
    """Use a consumable item in combat."""
    _rng = rng or random
    inv = state.get("inventory", [])

    # Find and remove item
    item_lower = item_name.strip().lower()
    found = False
    new_inv = []
    for item in inv:
        if not found and item.lower() == item_lower:
            found = True
            continue
        new_inv.append(item)

    if not found:
        return {"status": "error", "description": f"You don't have '{item_name}' in your inventory."}

    state["inventory"] = new_inv
    combat = state.get("combat", {})
    combat["player_moves_remaining"] = max(0, combat.get("player_moves_remaining", 1) - 1)

    # Simple item effects
    if "health" in item_lower or "potion" in item_lower:
        heal = _rng.randint(2, 8) + 2
        if "greater" in item_lower:
            heal = _rng.randint(4, 16) + 4
        state["hp"] = min(state.get("hp", 10) + heal, state.get("max_hp", 10))
        return {"status": "used", "description": f"You drink the {item_name} and recover {heal} HP!", "heal": heal}

    if "antidote" in item_lower:
        remove_status(state, "poison")
        return {"status": "used", "description": f"You use the {item_name}. Poison cured!"}

    return {"status": "used", "description": f"You use the {item_name}.", "item": item_name}


def resolve_flee(state: dict, rng: random.Random | None = None) -> dict:
    """Attempt to flee combat. DEX check vs DC 13. Opportunity attack on fail."""
    _rng = rng or random
    combat = state.get("combat", {})
    dex_mod = get_stat_modifier(state.get("stats", {}).get("DEX", 10))
    roll, _ = saving_throw(dex_mod, 0, _rng)
    dc = 13

    combat["player_moves_remaining"] = 0

    if roll >= dc:
        combat["active"] = False
        state["encounter_status"] = "none"
        state.pop("pending_encounter", None)
        return {"status": "escaped", "description": f"You manage to flee! (Rolled {roll} vs DC {dc})"}

    # Opportunity attack from first living enemy
    enemies = combat.get("enemies", [])
    oa_desc = ""
    for e in enemies:
        if e.get("alive", True):
            oa = resolve_enemy_turn(e, state, _rng)
            if oa.get("hit", False):
                state["hp"] = max(0, state.get("hp", 10) - oa["damage"])
            oa_desc = f" {e['display_name']} takes an opportunity attack! {oa['description']}"
            break

    return {
        "status": "failed",
        "description": f"Failed to flee! (Rolled {roll} vs DC {dc}).{oa_desc}",
    }


def combat_open_player_tick(state: dict, rng: random.Random | None = None) -> list[str]:
    """Tick statuses at the start of the player's turn."""
    _rng = rng or random
    msgs: list[str] = []

    # Tick statuses
    expired = tick_statuses(state, "combat_tick_player_start", _rng)
    for name in expired:
        msgs.append(f"**{name}** has worn off.")

    # Poison/bleed damage
    if has_status(state, "poison"):
        dmg = _rng.randint(1, 4)
        state["hp"] = max(0, state.get("hp", 10) - dmg)
        msgs.append(f"Poison courses through you! ({dmg} damage)")
    if has_status(state, "bleed"):
        dmg = _rng.randint(1, 4)
        state["hp"] = max(0, state.get("hp", 10) - dmg)
        msgs.append(f"Blood drips from your wounds! ({dmg} bleed damage)")

    # Reset moves
    combat = state.get("combat", {})
    if not is_stunned(state):
        combat["player_moves_remaining"] = 1
    else:
        combat["player_moves_remaining"] = 0
        msgs.append("You are **stunned** and cannot act this turn!")

    # Clear guard status after it expires (already handled by tick)

    return msgs


def combat_enemy_phase(state: dict, rng: random.Random | None = None) -> list[str]:
    """Execute each living enemy's turn."""
    _rng = rng or random
    combat = state.get("combat", {})
    enemies = combat.get("enemies", [])
    msgs: list[str] = []

    for e in enemies:
        if not e.get("alive", True):
            continue
        # Cooldown tick
        for ab_name in list(e.get("cooldowns", {})):
            e["cooldowns"][ab_name] = max(0, e["cooldowns"][ab_name] - 1)

        result = resolve_enemy_turn(e, state, _rng)
        if result.get("hit", True) and result.get("damage", 0) > 0:
            dmg = result["damage"]
            # Apply elemental
            elem = calculate_elemental_damage(
                dmg, result.get("damage_type", "physical"),
                {},  # player resistances — could be extended
                state.get("world", {}).get("weather"),
            )
            final = elem["final_damage"]
            state["hp"] = max(0, state.get("hp", 10) - final)
            msgs.append(f"{result['description']} ({final} damage)")
        else:
            msgs.append(result.get("description", f"{e['display_name']} does nothing."))

        # Check if player died
        if state.get("hp", 0) <= 0:
            msgs.append("You have been **defeated**!")
            break

    # Advance round
    combat["round"] = combat.get("round", 1) + 1
    return msgs


def check_combat_end(state: dict) -> str:
    """Return 'continue', 'victory', or 'defeat'."""
    combat = state.get("combat", {})
    if state.get("hp", 0) <= 0:
        return "defeat"
    enemies = combat.get("enemies", [])
    if all(not e.get("alive", True) for e in enemies):
        return "victory"
    return "continue"


def format_combat_banner(state: dict) -> str:
    """Render a combat status banner."""
    combat = state.get("combat", {})
    enemies = combat.get("enemies", [])
    hp = state.get("hp", 0)
    max_hp = state.get("max_hp", hp)
    bar = render_hp_bar(hp, max_hp)
    alive = [e for e in enemies if e.get("alive", True)]
    names = ", ".join(e["display_name"] for e in alive) if alive else "None"
    moves = combat.get("player_moves_remaining", 0)
    return (
        f"═══ Round {combat.get('round', 1)} ═══\n"
        f"Enemies: {names}\n"
        f"HP: {bar} {hp}/{max_hp}\n"
        f"Moves remaining: {moves}\n"
        f"─────────────────────"
    )


def format_combat_enemies_look(state: dict) -> str:
    """Describe all enemies in combat."""
    combat = state.get("combat", {})
    enemies = combat.get("enemies", [])
    lines = []
    for i, e in enumerate(enemies):
        status = "ALIVE" if e.get("alive", True) else "DEFEATED"
        bar = render_hp_bar(e.get("hp", 0), e.get("max_hp", 1))
        lines.append(f"  [{i}] {e['display_name']}: {bar} {e.get('hp',0)}/{e.get('max_hp',0)} [{status}]")
    return "Enemies:\n" + "\n".join(lines) if lines else "No enemies."
