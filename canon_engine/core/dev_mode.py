"""Canon Engine — Developer Mode Tools

Dev-only commands for testing and debugging.
Activated by CANON_ENGINE_DEV environment variable.

Public API:
    is_dev_mode() -> bool
    build_dev_warp_session() -> dict
    resolve_godmode(state) -> dict
    resolve_spawn(state, enemy_id, rng) -> dict
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any


# ── Content path ────────────────────────────────────────────────────────────

_CONTENT_DIR = Path(os.environ.get(
    "CANON_CONTENT_DIR",
    Path(__file__).resolve().parents[2] / "content",
))


def is_dev_mode() -> bool:
    """Check if CANON_ENGINE_DEV environment variable is set.

    Returns True if the var is set to any truthy value ("1", "true", "yes").
    """
    val = os.getenv("CANON_ENGINE_DEV", "").lower().strip()
    return val in ("1", "true", "yes", "on")


def build_dev_warp_session() -> dict:
    """Build a dev warp session.

    Loads dev_warp.json from content/ if available, otherwise generates
    a default dev session with high-level character and all areas unlocked.

    Returns a dict with keys: name, level, stats, gold, inventory, location, flags.
    """
    warp_path = _CONTENT_DIR / "dev_warp.json"
    if warp_path.exists():
        data = json.loads(warp_path.read_text(encoding="utf-8"))
        return data

    # Default dev session
    return {
        "name": "DevHero",
        "level": 20,
        "stats": {
            "STR": 20,
            "DEX": 20,
            "INT": 20,
            "CHA": 20,
            "CON": 20,
            "LCK": 20,
        },
        "gold": 99999,
        "inventory": [
            "Legendary Sword",
            "Dragon Plate Armor",
            "Health Potion x10",
            "Mana Potion x10",
            "Lockpick x20",
            "Torch x10",
        ],
        "location": "Dev Chamber",
        "flags": {
            "dev_mode": True,
            "god_mode": False,
            "all_areas_unlocked": True,
        },
    }


def resolve_godmode(state: dict[str, Any]) -> dict:
    """Set all player stats to 99 and restore full HP/MP/STM.

    Modifies state in-place.
    Returns a description dict.
    """
    player = state.get("player", state)

    # Set stats to 99
    stats = player.setdefault("stats", state.setdefault("stats", {}))
    for stat_key in ("STR", "DEX", "INT", "CHA", "CON", "LCK"):
        stats[stat_key] = 99

    # Full restore
    hp_max = 999
    player["hp"] = hp_max
    player["hp_max"] = hp_max
    player["mp"] = 999
    player["mp_max"] = 999
    player["stm"] = 999
    player["stm_max"] = 999

    # Set god mode flag
    state.setdefault("flags", {})["god_mode"] = True

    return {
        "success": True,
        "description": "⚡ GODMODE ACTIVATED — All stats set to 99, full HP/MP/STM restored.",
        "stats": dict(stats),
        "hp": hp_max,
    }


def resolve_spawn(state: dict[str, Any], enemy_id: str, rng: Any = None) -> dict:
    """Spawn an enemy by ID for testing.

    Looks up the enemy template from content/enemies.json and creates
    a live enemy instance in the combat state.

    Parameters
    ----------
    state : dict
        Mutable game state.
    enemy_id : str
        Enemy type ID (e.g. "bandit", "dragon", "skeleton").
    rng : Any
        Random number generator.

    Returns
    -------
    dict
        Result with keys: success, enemy, description.
    """
    _rng = rng or random.Random()

    # Load enemy templates
    enemies_path = _CONTENT_DIR / "enemies.json"
    templates: dict = {}
    if enemies_path.exists():
        data = json.loads(enemies_path.read_text(encoding="utf-8"))
        templates = data.get("enemies", data)

    # Find template
    template = templates.get(enemy_id)
    if template is None:
        # Fallback: create a basic enemy
        template = {
            "type": enemy_id,
            "hp_range": [10, 30],
            "ac": 10,
            "attack_mod": 2,
            "damage": "1d6",
            "xp": 25,
            "gold": [1, 10],
        }

    # Build enemy instance
    hp_range = template.get("hp_range", [10, 30])
    hp = _rng.randint(hp_range[0], hp_range[1])

    enemy = {
        "type": enemy_id,
        "display_name": enemy_id,
        "hp": hp,
        "max_hp": hp,
        "ac": template.get("ac", 10),
        "attack_mod": template.get("attack_mod", 2),
        "damage": template.get("damage", "1d6"),
        "damage_type": template.get("damage_type", "physical"),
        "abilities": template.get("abilities", []),
        "cooldowns": {},
        "resistances": template.get("resistances", {}),
        "xp": template.get("xp", 25),
        "gold": template.get("gold", [1, 10]),
        "loot_table": template.get("loot_table", []),
        "alive": True,
    }

    # Add to combat state
    combat = state.setdefault("combat", {"active": True, "enemies": [], "round": 1})
    combat["active"] = True
    combat.setdefault("enemies", []).append(enemy)
    combat.setdefault("round", 1)
    combat.setdefault("player_moves_remaining", 1)

    return {
        "success": True,
        "enemy": enemy,
        "description": f"Spawned {enemy_id} (HP: {hp}, AC: {enemy['ac']})",
    }
