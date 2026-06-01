"""
Canon Engine — Character Session Builder

Creates a fresh game session state from a character payload.
Bridges character creation (name, archetype, stats) into a full
playable game state ready for the narrator.

Public API:
    build_character_session_state(character: dict) -> dict
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Defaults and constants
# ---------------------------------------------------------------------------

_DEFAULT_STATS = {
    "STR": 10, "DEX": 10, "INT": 10,
    "CHA": 10, "CON": 10, "LCK": 10,
}

_ARCHETYPE_DEFAULTS = {
    "knight": {"STR": 14, "DEX": 10, "INT": 8, "CHA": 12, "CON": 13, "LCK": 8},
    "rogue": {"STR": 8, "DEX": 15, "INT": 12, "CHA": 10, "CON": 9, "LCK": 13},
    "mage": {"STR": 6, "DEX": 8, "INT": 16, "CHA": 11, "CON": 8, "LCK": 10},
    "ranger": {"STR": 11, "DEX": 14, "INT": 10, "CHA": 8, "CON": 12, "LCK": 10},
    "cleric": {"STR": 10, "DEX": 8, "INT": 12, "CHA": 13, "CON": 12, "LCK": 10},
    "bard": {"STR": 8, "DEX": 12, "INT": 12, "CHA": 15, "CON": 9, "LCK": 11},
}

_GENRE_TONES = {
    "medieval_fantasy": "epic and grounded",
    "space_opera": "grand and adventurous",
    "gothic_horror": "dark and foreboding",
    "western": "gritty and sun-scorched",
    "anime_dramatic": "intense and emotional",
    "cyberpunk": "neon-lit and dystopian",
    "post_apocalyptic": "desolate and hopeful",
}

_GENRE_LOCATIONS = {
    "medieval_fantasy": "The Crossroads Inn, a weathered tavern at the edge of the known world",
    "space_opera": "Deck 7 of the Waystation Helix, a bustling orbital hub",
    "gothic_horror": "The fog-choked outskirts of Hollow Creek",
    "western": "The dusty platform of Dry Gulch Station",
    "anime_dramatic": "The gates of the Academy of Rising Blades",
    "cyberpunk": "A rain-slicked alley in Neon District 9",
    "post_apocalyptic": "The ruins of what was once a gas station on Highway 12",
}

_GENRE_BIBLES = {
    "medieval_fantasy": (
        "A world of swords and sorcery. Kingdoms rise and fall on the whims of "
        "dragon-riding monarchs. Magic is real but dangerous — every spell exacts a toll. "
        "The common folk whisper of an ancient prophecy that speaks of a hero who will "
        "either save or doom the realm."
    ),
    "space_opera": (
        "The galaxy is a web of alliances and betrayals. Faster-than-light travel is "
        "controlled by the Gate Network, and those who control the gates control civilization. "
        "Alien species coexist uneasily, and a shadowy empire seeks to bring all worlds "
        "under one banner."
    ),
    "gothic_horror": (
        "The world is shrouded in perpetual twilight. Ancient evils stir in crypts and "
        "cathedrals. The Church claims to protect the living, but its inquisitors have "
        "secrets of their own. Curses are real, and the dead do not always stay buried."
    ),
    "western": (
        "The frontier is lawless and vast. Railroads are pushing civilization westward, "
        "displacing everyone in their path. Outlaws, lawmen, and fortune-seekers clash "
        "under a relentless sun. Every town has a story, and most of them end badly."
    ),
    "anime_dramatic": (
        "A world where martial arts and magic intertwine. Ancient clans guard forbidden "
        "techniques passed down through generations. Tournaments determine fates, and a "
        "sealed evil stirs beneath the earth, waiting for the one prophesied to either "
        "unleash or destroy it."
    ),
}


# ---------------------------------------------------------------------------
# Helper: safe dict access
# ---------------------------------------------------------------------------

def _get_stat(character: dict, key: str, default: int = 10) -> int:
    """Get a stat value from character, trying both nested and flat access."""
    stats = character.get("stats", {})
    if isinstance(stats, dict) and key in stats:
        return int(stats[key])
    if key in character:
        return int(character[key])
    return default


def _get(character: dict, key: str, default: Any = None) -> Any:
    """Get a value from character dict with a default."""
    return character.get(key, default)


# ---------------------------------------------------------------------------
# Ensure helpers (gracefully degrade if modules missing)
# ---------------------------------------------------------------------------

def _try_ensure_world(state: dict) -> None:
    """Call ensure_world if available."""
    try:
        from canon_engine.core.world import ensure_world
        ensure_world(state)
    except (ImportError, AttributeError):
        # Provide minimal world structure
        state.setdefault("world", {
            "time_of_day": "morning",
            "weather": "clear",
            "season": "spring",
        })


def _try_ensure_inventory_items(state: dict) -> None:
    """Call ensure_inventory_items if available."""
    try:
        from canon_engine.core.inventory import ensure_inventory_items
        ensure_inventory_items(state)
    except (ImportError, AttributeError):
        pass


def _try_ensure_equipment(state: dict) -> None:
    """Set up default equipment slots."""
    try:
        from canon_engine.core.inventory import ensure_equipment
        ensure_equipment(state)
    except (ImportError, AttributeError):
        # Provide minimal equipment structure
        state.setdefault("equipment", {
            "weapon": None,
            "armor": None,
            "helmet": None,
            "boots": None,
            "accessory": None,
        })


def _try_calculate_max_hp(stats: dict, level: int = 1) -> int:
    """Calculate max HP using stats module if available."""
    try:
        from canon_engine.core.stats import calculate_max_hp
        return calculate_max_hp(stats, level)
    except (ImportError, AttributeError):
        return 100 + (stats.get("CON", 10) - 10) * 5 + (level - 1) * 10


def _try_calculate_max_mp(stats: dict, level: int = 1) -> int:
    """Calculate max MP using stats module if available."""
    try:
        from canon_engine.core.stats import calculate_max_mp
        return calculate_max_mp(stats, level)
    except (ImportError, AttributeError):
        return 50 + (stats.get("INT", 10) - 10) * 3 + (level - 1) * 5


def _try_calculate_max_stm(stats: dict, level: int = 1) -> int:
    """Calculate max stamina using stats module if available."""
    try:
        from canon_engine.core.stats import calculate_max_stm
        return calculate_max_stm(stats, level)
    except (ImportError, AttributeError):
        return 80 + (stats.get("CON", 10) - 10) * 2 + (level - 1) * 5


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def build_character_session_state(character: dict) -> dict:
    """
    Create a fresh game session state from a character payload.

    Parameters
    ----------
    character : dict
        Character creation data. Expected keys:
        - name: str
        - archetype: str (knight, rogue, mage, ranger, cleric, bard, etc.)
        - race: str (human, elf, dwarf, halfling, orc, etc.)
        - stats: dict (STR, DEX, INT, CHA, CON, LCK) — optional, falls back to archetype defaults
        - genre / setting: str — determines world_bible, tone, location
        - backstory: str — optional
        - speech: str — optional speech style
        - gender: str — optional

    Returns
    -------
    dict
        Complete game state dict ready for play.
    """
    # --- Player basics ---
    archetype = _get(character, "archetype", "adventurer").lower()
    race = _get(character, "race", "human")
    name = _get(character, "name", "Adventurer")
    level = int(_get(character, "level", 1))
    gender = _get(character, "gender", "")

    # --- Stats ---
    archetype_stats = _ARCHETYPE_DEFAULTS.get(archetype, _DEFAULT_STATS)
    stats = {}
    for key in ("STR", "DEX", "INT", "CHA", "CON", "LCK"):
        stats[key] = _get_stat(character, key, archetype_stats.get(key, 10))

    # --- Derived attributes ---
    max_hp = _try_calculate_max_hp(stats, level)
    max_mp = _try_calculate_max_mp(stats, level)
    max_stm = _try_calculate_max_stm(stats, level)

    # --- Genre / setting ---
    genre = _get(character, "genre", _get(character, "setting", "medieval_fantasy"))
    genre = genre.lower().replace(" ", "_").replace("-", "_")
    tone = _get(character, "tone", _GENRE_TONES.get(genre, "epic and grounded"))
    location = _get(character, "location", _GENRE_LOCATIONS.get(genre, "A crossroads"))
    world_bible = _get(character, "world_bible", _GENRE_BIBLES.get(genre, ""))
    speech = _get(character, "speech", "Casual")
    backstory = _get(character, "backstory", "")

    # --- Starting inventory ---
    starting_inventory = _get(character, "inventory", [])
    if not isinstance(starting_inventory, list):
        starting_inventory = []

    # Ensure starting items are normalized
    normalized_inventory = []
    for item in starting_inventory:
        if isinstance(item, dict):
            normalized_inventory.append({
                "name": str(item.get("name", "Unknown")),
                "rarity": str(item.get("rarity", "common")),
            })
        elif isinstance(item, str):
            normalized_inventory.append({"name": item, "rarity": "common"})

    # --- Build state ---
    state: Dict[str, Any] = {
        # Player block
        "player": {
            "name": name,
            "archetype": archetype,
            "race": race,
            "gender": gender,
            "level": level,
            "xp": int(_get(character, "xp", 0)),
            "xp_to_next": int(_get(character, "xp_to_next", 100)),
            "hp": int(_get(character, "hp", max_hp)),
            "max_hp": max_hp,
            "mp": int(_get(character, "mp", max_mp)),
            "max_mp": max_mp,
            "stm": int(_get(character, "stm", max_stm)),
            "max_stm": max_stm,
            "gold": int(_get(character, "gold", 10)),
            "stats": stats,
            "stat_points": int(_get(character, "stat_points", 0)),
            "speech": speech,
            "backstory": backstory,
        },

        # World state
        "location": location,
        "genre": genre,
        "tone": tone,
        "world_bible": world_bible,

        # Inventory & equipment
        "inventory": normalized_inventory,
        "equipment": {},

        # Logs
        "world_log": [],
        "command_log": [],
        "checks": [],
        "lore_entries": [],

        # Quest state
        "quests": {
            "active": [],
            "completed": [],
        },

        # Saga (major story arc)
        "saga": {
            "title": "",
            "summary": "",
            "turn": 0,
            "milestone": False,
        },

        # Flags (arbitrary game flags)
        "flags": {},

        # Memory (rolling narrative summary)
        "memory": {
            "summary": "",
            "last_update_turn": 0,
        },

        # Combat (starts empty)
        "combat": {
            "active": False,
            "enemies": [],
            "round": 0,
        },

        # Tutorial
        "tutorial": {
            "active": False,
            "step": 0,
            "completed": False,
        },

        # World time
        "turn": 0,

        # Setting overrides (for genre collisions etc.)
        "setting_overrides": {},

        # Companions
        "companions": [],
    }

    # --- Call ensure helpers ---
    _try_ensure_world(state)
    _try_ensure_inventory_items(state)
    _try_ensure_equipment(state)

    return state
