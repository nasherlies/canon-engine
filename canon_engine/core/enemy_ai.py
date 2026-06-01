"""Canon Engine — Enemy AI

Defines enemy archetypes and a simple intent-based AI that selects
abilities or basic attacks during the enemy combat phase.
"""
from __future__ import annotations
import random
from typing import Any

# ---------------------------------------------------------------------------
# Enemy type catalogue
# ---------------------------------------------------------------------------

ENEMY_TYPES: dict[str, dict[str, Any]] = {
    "skeleton": {
        "hp_range": (8, 14),
        "ac": 13,
        "attack_mod": 4,
        "damage": (1, 6),
        "damage_type": "physical",
        "abilities": [
            {"name": "Bone Rattle", "cooldown": 3, "damage": (1, 8), "damage_type": "thunder", "description": "Rattles bones to produce a disorienting shockwave."},
        ],
        "resistances": {"piercing": "resistant", "cold": "immune"},
        "perception_dc": 10,
        "xp": 50,
        "gold": (1, 8),
        "loot_table": ["bone_shard", "rusty_sword"],
    },
    "guard": {
        "hp_range": (18, 26),
        "ac": 16,
        "attack_mod": 5,
        "damage": (1, 8),
        "damage_type": "physical",
        "abilities": [
            {"name": "Shield Bash", "cooldown": 2, "damage": (1, 6), "damage_type": "physical", "description": "Slams shield into the foe, staggering them."},
        ],
        "resistances": {},
        "perception_dc": 13,
        "xp": 100,
        "gold": (5, 15),
        "loot_table": ["iron_shield", "guard_badge"],
    },
    "beast": {
        "hp_range": (12, 20),
        "ac": 12,
        "attack_mod": 4,
        "damage": (1, 6),
        "damage_type": "physical",
        "abilities": [
            {"name": "Savage Bite", "cooldown": 2, "damage": (2, 6), "damage_type": "physical", "description": "A vicious bite aimed at a vulnerable spot."},
        ],
        "resistances": {},
        "perception_dc": 14,
        "xp": 75,
        "gold": (0, 3),
        "loot_table": ["beast_hide", "fang"],
    },
    "goblin": {
        "hp_range": (5, 10),
        "ac": 13,
        "attack_mod": 4,
        "damage": (1, 6),
        "damage_type": "physical",
        "abilities": [
            {"name": "Dirty Trick", "cooldown": 3, "damage": (1, 4), "damage_type": "poison", "description": "Throws pocket sand laced with mild venom."},
        ],
        "resistances": {},
        "perception_dc": 9,
        "xp": 25,
        "gold": (1, 6),
        "loot_table": ["goblin_ear", "crude_dagger"],
    },
    "bandit": {
        "hp_range": (10, 18),
        "ac": 12,
        "attack_mod": 3,
        "damage": (1, 6),
        "damage_type": "physical",
        "abilities": [
            {"name": "Sneak Attack", "cooldown": 3, "damage": (2, 6), "damage_type": "physical", "description": "A cunning strike from an unexpected angle."},
        ],
        "resistances": {},
        "perception_dc": 11,
        "xp": 50,
        "gold": (3, 12),
        "loot_table": ["bandit_mask", "stolen_coinpurse"],
    },
    "undead_soldier": {
        "hp_range": (20, 30),
        "ac": 15,
        "attack_mod": 5,
        "damage": (1, 8),
        "damage_type": "physical",
        "abilities": [
            {"name": "Unholy Strike", "cooldown": 2, "damage": (1, 10), "damage_type": "necrotic", "description": "Channels dark energy through the blade."},
        ],
        "resistances": {"necrotic": "immune", "poison": "immune"},
        "perception_dc": 12,
        "xp": 120,
        "gold": (5, 20),
        "loot_table": ["dark_essence", "rusted_helm"],
    },
    "wolf": {
        "hp_range": (8, 14),
        "ac": 13,
        "attack_mod": 4,
        "damage": (1, 6),
        "damage_type": "physical",
        "abilities": [
            {"name": "Pack Howl", "cooldown": 4, "damage": (0, 0), "damage_type": "physical", "description": "Howls to boost pack morale — buffs own ATK."},
            {"name": "Savage Bite", "cooldown": 2, "damage": (2, 4), "damage_type": "physical", "description": "A tearing bite at the throat."},
        ],
        "resistances": {},
        "perception_dc": 15,
        "xp": 40,
        "gold": (0, 2),
        "loot_table": ["wolf_pelt", "fang"],
    },
    "spider": {
        "hp_range": (6, 12),
        "ac": 12,
        "attack_mod": 3,
        "damage": (1, 4),
        "damage_type": "poison",
        "abilities": [
            {"name": "Web Shot", "cooldown": 3, "damage": (0, 0), "damage_type": "physical", "description": "Sprays sticky web to entangle the target."},
            {"name": "Venomous Bite", "cooldown": 2, "damage": (1, 6), "damage_type": "poison", "description": "Injects venom through razor fangs."},
        ],
        "resistances": {"poison": "resistant"},
        "perception_dc": 11,
        "xp": 35,
        "gold": (0, 2),
        "loot_table": ["spider_silk", "venom_sac"],
    },
    "cultist": {
        "hp_range": (10, 18),
        "ac": 12,
        "attack_mod": 3,
        "damage": (1, 6),
        "damage_type": "physical",
        "abilities": [
            {"name": "Dark Invocation", "cooldown": 3, "damage": (2, 6), "damage_type": "necrotic", "description": "Channels forbidden power into a burst of dark energy."},
        ],
        "resistances": {"necrotic": "resistant"},
        "perception_dc": 10,
        "xp": 60,
        "gold": (2, 10),
        "loot_table": ["occult_symbol", "dark_scroll"],
    },
    "demon": {
        "hp_range": (30, 50),
        "ac": 16,
        "attack_mod": 7,
        "damage": (2, 6),
        "damage_type": "fire",
        "abilities": [
            {"name": "Hellfire", "cooldown": 3, "damage": (3, 6), "damage_type": "fire", "description": "Erupts with infernal flame."},
            {"name": "Terror Gaze", "cooldown": 4, "damage": (1, 4), "damage_type": "psychic", "description": "Locks eyes with the target, filling them with dread."},
        ],
        "resistances": {"fire": "resistant", "poison": "immune", "necrotic": "resistant"},
        "perception_dc": 16,
        "xp": 300,
        "gold": (20, 50),
        "loot_table": ["demon_horn", "infernal_essence"],
    },
}


# ---------------------------------------------------------------------------
# Enemy turn resolution
# ---------------------------------------------------------------------------

def _determine_intent(enemy: dict, player: dict) -> str:
    """Pick intent based on HP ratios."""
    e_hp_pct = enemy.get("hp", 1) / max(enemy.get("max_hp", 1), 1)
    p_hp_pct = player.get("hp", 1) / max(player.get("max_hp", 1), 1)
    if e_hp_pct < 0.3:
        return "defensive"
    if p_hp_pct < 0.3:
        return "desperate"
    return "aggressive"


def resolve_enemy_turn(enemy: dict, player: dict, rng: random.Random | None = None) -> dict:
    """Decide and execute an enemy's turn.

    Parameters
    ----------
    enemy : dict  — live enemy dict (has hp, max_hp, type, abilities, cooldowns, etc.)
    player : dict — player state
    rng    : Random instance

    Returns
    -------
    dict with keys: action, target, damage, damage_type, description, hit
    """
    _rng = rng or random
    intent = _determine_intent(enemy, player)

    # Try an ability first (if off cooldown)
    abilities = enemy.get("abilities", [])
    cooldowns = enemy.get("cooldowns", {})

    chosen_ability = None
    for ab in abilities:
        cd_left = cooldowns.get(ab["name"], 0)
        if cd_left <= 0:
            # For desperate intent, prefer highest-damage ability
            chosen_ability = ab
            break

    if intent == "defensive" and chosen_ability is None:
        # Just basic attack when defensive and nothing off cooldown
        pass

    if chosen_ability:
        # Set cooldown
        enemy.setdefault("cooldowns", {})[chosen_ability["name"]] = chosen_ability["cooldown"]
        n, sides = chosen_ability["damage"]
        if n == 0 and sides == 0:
            # Non-damage ability (e.g. buff/debuff)
            return {
                "action": "ability",
                "ability_name": chosen_ability["name"],
                "target": "self",
                "damage": 0,
                "damage_type": chosen_ability.get("damage_type", "physical"),
                "description": chosen_ability["description"],
                "hit": True,
                "intent": intent,
            }
        dmg = sum(_rng.randint(1, sides) for _ in range(n))
        return {
            "action": "ability",
            "ability_name": chosen_ability["name"],
            "target": "player",
            "damage": dmg,
            "damage_type": chosen_ability.get("damage_type", "physical"),
            "description": chosen_ability["description"],
            "hit": True,
            "intent": intent,
        }

    # Basic attack
    from .combat_math import attack_roll, damage_roll
    atk_mod = enemy.get("attack_mod", 0)
    total, is_crit, is_fumble = attack_roll(atk_mod, 0, _rng)
    player_ac = player.get("ac", 10)

    if is_fumble:
        return {
            "action": "attack",
            "target": "player",
            "damage": 0,
            "damage_type": enemy.get("damage_type", "physical"),
            "description": f"{enemy.get('display_name', enemy.get('type', 'enemy'))} swings wildly and misses!",
            "hit": False,
            "crit": False,
            "fumble": True,
            "intent": intent,
        }

    hit = total >= player_ac or is_crit
    dmg = 0
    if hit:
        dmg = damage_roll(enemy.get("damage", (1, 6)), 0, is_crit, _rng)

    crit_text = " **CRITICAL HIT!**" if is_crit else ""
    verb = "strikes" if hit else "misses"
    name = enemy.get("display_name", enemy.get("type", "enemy"))
    return {
        "action": "attack",
        "target": "player",
        "damage": dmg,
        "damage_type": enemy.get("damage_type", "physical"),
        "description": f"{name} {verb} you!{crit_text}" + (f" ({dmg} damage)" if dmg else ""),
        "hit": hit,
        "crit": is_crit,
        "fumble": False,
        "intent": intent,
    }
