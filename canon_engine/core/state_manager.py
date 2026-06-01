"""State manager – atomic save/load with legacy-merge support."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path


# ── Exceptions ────────────────────────────────────────────────────────────

class SaveValidationError(Exception):
    """Raised when a save file fails validation."""


# ── Default state shape ───────────────────────────────────────────────────

_DEFAULT_STATE: dict = {
    "save_version": 1,
    "player": {
        "name": "",
        "hp": 100,
        "hp_max": 100,
        "mp": 50,
        "mp_max": 50,
        "stm": 100,
        "stm_max": 100,
        "xp": 0,
        "xp_to_next": 100,
        "level": 1,
        "stat_points": 0,
        "stats": {
            "STR": 10,
            "DEX": 10,
            "INT": 10,
            "CHA": 10,
            "CON": 10,
            "LCK": 10,
        },
        "statuses": [],
        "alive": True,
        "gold": 0,
        "gold_spent": 0,
    },
    "inventory": [],
    "equipment": {},
    "companions": [],
    "world": {
        "location": "Unknown",
        "location_id": "",
        "minutes_total": 480,
        "weather": "clear",
        "weather_icon": "☀",
        "sheltered": False,
        "fatigue": False,
        "quests": {
            "active": {},
            "completed": {},
            "failed": {},
        },
        "npcs": {},
        "flags": {},
        "travel_edges": [],
    },
    "world_flags": {},
    "world_bible": {},
    "world_log": [],
    "command_log": [],
    "memory": {
        "summary": "",
        "last_summary_turn": 0,
    },
    "combat": {
        "active": False,
    },
    "tutorial": {
        "active": False,
    },
    "turn": 0,
    "active_slot": "",
    "lore_cards": [],
    "saga": {
        "phase": 0,
        "flags": [],
    },
    "honor_score": 0,
    "chaos_score": 0,
    "fallen_heroes": [],
    "equipment_legacy_migrated": False,
}


# ── Merge helper ──────────────────────────────────────────────────────────

def _merge_legacy_save_shape(state: dict) -> dict:
    """Fill any missing top-level and second-level keys from defaults."""
    merged = copy.deepcopy(_DEFAULT_STATE)
    for key, value in state.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


# ── Public API ────────────────────────────────────────────────────────────

def save_game(state: dict, path: str) -> None:
    """Atomic write: write to ``path + '.tmp'`` then ``os.replace``."""
    final = Path(path)
    tmp = final.with_suffix(final.suffix + ".tmp")
    data = json.dumps(state, indent=2, ensure_ascii=False)
    tmp.write_text(data, encoding="utf-8")
    os.replace(str(tmp), str(final))


def load_game(path: str) -> dict:
    """Load a JSON save, validate version, and merge legacy defaults."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Save file not found: {path}")

    raw = p.read_text(encoding="utf-8")
    try:
        state = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SaveValidationError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(state, dict):
        raise SaveValidationError(
            f"Save file must be a JSON object, got {type(state).__name__}"
        )

    version = state.get("save_version")
    if version != 1:
        raise SaveValidationError(
            f"Unsupported save_version {version!r} (expected 1)"
        )

    return _merge_legacy_save_shape(state)
