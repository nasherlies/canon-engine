"""Character creation, stat management, HP calculation, leveling helpers."""

from __future__ import annotations

import random
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_STATS = {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}
ALL_STATS = list(BASE_STATS.keys())

# ---------------------------------------------------------------------------
# Core formulas
# ---------------------------------------------------------------------------

def score_to_modifier(score: int) -> int:
    """Return the d20-style modifier for a stat score."""
    return (score - 10) // 2


def max_hp(con: int, level: int = 1) -> int:
    """max_hp = 50 + CON * 5.  Level scaling can be added later."""
    return 50 + con * 5


def xp_to_next(level: int) -> int:
    """XP required to advance from *level* to *level+1*."""
    return level * 100


def proficiency_bonus(level: int) -> int:
    """D&D 5e proficiency bonus scaling.
    2 + (level - 1) // 4
    L1-4=+2, L5-8=+3, L9-12=+4, L13-16=+5, L17-20=+6."""
    return 2 + (level - 1) // 4


# ---------------------------------------------------------------------------
# Character creation
# ---------------------------------------------------------------------------

def create_character(name: str, race: str = "Human", klass: str = "Adventurer") -> dict[str, Any]:
    """Return a fresh character sheet dict."""
    stats = {k: random.randint(8, 16) for k in ALL_STATS}
    hp = max_hp(stats["CON"])
    return {
        "name": name,
        "race": race,
        "class": klass,
        "level": 1,
        "xp": 0,
        "stats": stats,
        "hp": hp,
        "max_hp": hp,
        "temp_hp": 0,
        "ac": 10 + score_to_modifier(stats["DEX"]),
        "proficiency_bonus": 2,
        "skill_points": 0,
        "skills": [],
        "conditions": [],
    }


def apply_damage(state: dict[str, Any], amount: int) -> dict[str, Any]:
    """Reduce HP by *amount*, returning damage result."""
    char = state.get("player", state.get("character", state))
    absorbed = min(amount, char.get("temp_hp", 0))
    char["temp_hp"] = max(0, char.get("temp_hp", 0) - absorbed)
    remaining = amount - absorbed
    char["hp"] = max(0, char.get("hp", 0) - remaining)
    return {"damage": amount, "absorbed": absorbed, "remaining_hp": char["hp"]}


def heal(state: dict[str, Any], amount: int) -> int:
    """Heal HP up to max_hp.  Returns actual amount healed."""
    char = state.get("player", state.get("character", state))
    before = char["hp"]
    char["hp"] = min(char["max_hp"], char["hp"] + amount)
    return char["hp"] - before


def level_up(state: dict[str, Any]) -> dict[str, Any]:
    """Attempt to level up if enough XP.  Returns event dict."""
    char = state.get("player", state.get("character", state))
    char.setdefault("level", 1)
    char.setdefault("xp", 0)
    needed = xp_to_next(char["level"])
    if char["xp"] < needed:
        return {"leveled": False, "xp_needed": needed}
    char["xp"] -= needed
    char["level"] += 1
    char["max_hp"] = max_hp(char["stats"]["CON"], char["level"])
    char["hp"] = char["max_hp"]
    char["skill_points"] = char.get("skill_points", 0) + 2
    # Update proficiency bonus on level up
    char["proficiency_bonus"] = proficiency_bonus(char["level"])
    return {"leveled": True, "new_level": char["level"]}
