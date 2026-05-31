"""Combat terrain features."""

from __future__ import annotations

from typing import Any

TERRAIN_FEATURES = {
    "difficult": {"movement_cost": 2, "description": "Difficult terrain"},
    "elevated": {"ranged_bonus": 2, "description": "Elevated position"},
    "cover": {"ac_bonus": 2, "description": "Partial cover"},
    "hazard": {"damage_per_turn": 3, "damage_type": "fire", "description": "Hazardous terrain"},
    "slippery": {"save_dc": 12, "effect": "prone", "description": "Slippery surface"},
}


def get_terrain(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault("terrain", {"features": []})


def add_terrain_feature(state: dict[str, Any], feature_name: str) -> bool:
    template = TERRAIN_FEATURES.get(feature_name)
    if template is None:
        return False
    get_terrain(state).setdefault("features", []).append({**template, "name": feature_name})
    return True


def describe_terrain(state: dict[str, Any]) -> str:
    features = get_terrain(state).get("features", [])
    if not features:
        return "The terrain offers no notable features."
    return "Terrain: " + ", ".join(f.get("description", f["name"]) for f in features)
