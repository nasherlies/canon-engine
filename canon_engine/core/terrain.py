"""Canon Engine — Terrain & Environmental Tactics

Terrain features modify combat: hazards deal damage, cover grants AC bonuses,
elevation grants attack bonuses, and narrow passages cap enemy count.
"""
from __future__ import annotations

import random
from typing import Any

from .combat_math import d20, roll_dice
from .stats import get_stat_modifier


# ---------------------------------------------------------------------------
# Terrain feature registry
# ---------------------------------------------------------------------------


TERRAIN_FEATURES: dict[str, dict[str, Any]] = {
    "oil_barrel": {
        "type": "hazard",
        "damage": (2, 6),
        "element": "fire",
        "trigger": "attack_nearby",
    },
    "chandelier": {
        "type": "hazard",
        "damage": (3, 6),
        "element": "physical",
        "trigger": "interact",
        "aoe": True,
    },
    "narrow_passage": {
        "type": "cap",
        "max_enemies": 1,
    },
    "cover_wall": {
        "type": "cover",
        "ac_bonus": 2,
        "clear_on": ["attack", "travel"],
    },
    "high_ground": {
        "type": "elevation",
        "attack_bonus": 2,
        "clear_on": ["flee", "combat"],
    },
    "ice_floor": {
        "type": "hazard",
        "trigger": "nat1_attack",
        "effect": "prone",
    },
}


# ---------------------------------------------------------------------------
# Terrain modifiers
# ---------------------------------------------------------------------------


def get_terrain_modifiers(state: dict[str, Any]) -> dict[str, Any]:
    """Read terrain features from state.world.location or state.world_flags.

    Returns a dict mapping feature_name → feature_dict for active terrain.
    """
    world = state.get("world", {})
    flags = state.get("world_flags", {})

    active: dict[str, Any] = {}

    # Check location-based terrain
    location_terrain = world.get("terrain_features", [])
    if isinstance(location_terrain, list):
        for feat_name in location_terrain:
            if feat_name in TERRAIN_FEATURES:
                active[feat_name] = dict(TERRAIN_FEATURES[feat_name])
    elif isinstance(location_terrain, dict):
        for feat_name, feat_data in location_terrain.items():
            if feat_name in TERRAIN_FEATURES:
                merged = dict(TERRAIN_FEATURES[feat_name])
                merged.update(feat_data)
                active[feat_name] = merged

    # Check world flags for terrain markers
    terrain_flags = flags.get("terrain", {})
    if isinstance(terrain_flags, dict):
        for feat_name, feat_data in terrain_flags.items():
            if feat_name in TERRAIN_FEATURES and feat_name not in active:
                merged = dict(TERRAIN_FEATURES[feat_name])
                if isinstance(feat_data, dict):
                    merged.update(feat_data)
                active[feat_name] = merged

    return active


def world_combat_stat_adjust(
    state: dict[str, Any],
    stat_name: str,
    base_value: int,
) -> int:
    """Apply terrain modifiers to a combat stat.

    Supports: 'attack' (high_ground bonus), 'ac' (cover bonus).
    """
    terrain = get_terrain_modifiers(state)
    adjusted = base_value

    for feat_name, feat in terrain.items():
        if feat.get("type") == "elevation" and stat_name == "attack":
            adjusted += feat.get("attack_bonus", 0)
        elif feat.get("type") == "cover" and stat_name == "ac":
            adjusted += feat.get("ac_bonus", 0)

    return adjusted


def enemy_ac_terrain_adjust(state: dict[str, Any], base_ac: int) -> int:
    """Terrain AC adjustments — e.g., enemies behind cover get AC bonus."""
    terrain = get_terrain_modifiers(state)
    ac = base_ac
    for feat in terrain.values():
        if feat.get("type") == "cover":
            ac += feat.get("ac_bonus", 0)
    return ac


# ---------------------------------------------------------------------------
# Narrow passage
# ---------------------------------------------------------------------------


def start_combat_trim_enemies(
    state: dict[str, Any],
    enemies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Cap enemy count to narrow passage limit if present."""
    terrain = get_terrain_modifiers(state)
    cap = None
    for feat in terrain.values():
        if feat.get("type") == "cap":
            cap = feat.get("max_enemies", None)
            break
    if cap is not None and len(enemies) > cap:
        return enemies[:cap]
    return enemies


# ---------------------------------------------------------------------------
# Hazard ticking
# ---------------------------------------------------------------------------


def terrain_hazards_tick(
    state: dict[str, Any],
    rng: random.Random | None = None,
) -> list[str]:
    """Trigger environmental hazards at the start of the enemy phase.

    Returns list of narration strings describing hazard effects.
    """
    _rng = rng or random
    terrain = get_terrain_modifiers(state)
    messages: list[str] = []

    for feat_name, feat in terrain.items():
        if feat.get("type") != "hazard":
            continue
        trigger = feat.get("trigger", "")
        # Only trigger periodic hazards here (not nat1 or interact)
        if trigger not in ("turn_start", "periodic", "attack_nearby"):
            continue
        dmg_range = feat.get("damage")
        if dmg_range:
            dmg = _rng.randint(dmg_range[0], dmg_range[1])
            element = feat.get("element", "physical")
            messages.append(f"The {feat_name.replace('_', ' ')} erupts! {dmg} {element} damage.")

    return messages


# ---------------------------------------------------------------------------
# Feature interaction
# ---------------------------------------------------------------------------


def apply_feature_interaction(
    state: dict[str, Any],
    feature_name: str,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Trigger an interactive terrain feature (oil barrel, chandelier, etc.).

    Returns dict with: feature, damage, element, aoe, narration.
    """
    _rng = rng or random
    feat = TERRAIN_FEATURES.get(feature_name)
    if feat is None:
        return {"narration": f"No feature named '{feature_name}' found."}

    dmg_range = feat.get("damage")
    damage = 0
    if dmg_range:
        damage = _rng.randint(dmg_range[0], dmg_range[1])

    element = feat.get("element", "physical")
    aoe = feat.get("aoe", False)

    narration = f"You trigger the {feature_name.replace('_', ' ')}! "
    if aoe:
        narration += f"All enemies take {damage} {element} damage!"
    else:
        narration += f"Deals {damage} {element} damage!"

    return {
        "feature": feature_name,
        "damage": damage,
        "element": element,
        "aoe": aoe,
        "narration": narration,
    }


# ---------------------------------------------------------------------------
# Cover & Climb
# ---------------------------------------------------------------------------


def resolve_cover(state: dict[str, Any]) -> dict[str, Any]:
    """Take cover behind terrain. Grants +2 AC via 'covered' status.

    Returns dict with: ac_bonus, narration.
    """
    terrain = get_terrain_modifiers(state)
    has_cover_source = any(f.get("type") in ("cover", "hazard") for f in terrain.values())

    # Also allow cover even without terrain (generic action)
    ac_bonus = 2
    if has_cover_source:
        ac_bonus = 3  # Better cover with actual terrain

    return {
        "ac_bonus": ac_bonus,
        "narration": f"You take cover! (+{ac_bonus} AC)",
    }


def resolve_climb(
    state: dict[str, Any],
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Climb check — DEX DC 13.

    Returns dict with: success, roll, dc, narration.
    """
    _rng = rng or random
    dc = 13
    dex_mod = get_stat_modifier(state.get("stats", {}).get("DEX", 10))
    roll = d20(_rng)
    total = roll + dex_mod
    success = roll == 20 or (roll != 1 and total >= dc)

    if success:
        narration = f"You climb up! (rolled {total} vs DC {dc})"
    else:
        narration = f"You slip and fall! (rolled {total} vs DC {dc})"

    return {"success": success, "roll": roll, "total": total, "dc": dc, "narration": narration}


# ---------------------------------------------------------------------------
# Ice floor — nat 1 slip
# ---------------------------------------------------------------------------


def on_player_attack_roll(
    state: dict[str, Any],
    roll: int,
    rng: random.Random | None = None,
) -> tuple[int, str]:
    """Check for ice floor nat-1 slip on player attack.

    Returns (modified_roll, narration).  If nat-1 on ice, returns (-1, slip_msg).
    Otherwise returns (roll, "").
    """
    terrain = get_terrain_modifiers(state)
    has_ice = any(
        feat.get("type") == "hazard" and feat.get("effect") == "prone"
        for feat in terrain.values()
    )

    if has_ice and roll == 1:
        return (-1, "You slip on the icy floor and fall prone!")
    return (roll, "")
