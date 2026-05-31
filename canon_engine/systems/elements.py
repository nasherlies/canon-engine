"""Damage types and resistances."""

from __future__ import annotations

from typing import Any

DAMAGE_TYPES = ["physical", "fire", "frost", "lightning", "holy", "void"]


def get_resistances(state: dict[str, Any]) -> dict[str, float]:
    """Return resistance map (0.0 = immune, 0.5 = half, 1.0 = normal, 2.0 = vulnerable)."""
    return state.setdefault("resistances", {dt: 1.0 for dt in DAMAGE_TYPES})


def apply_resistance(raw_damage: int, damage_type: str, resistances: dict[str, float]) -> int:
    mult = resistances.get(damage_type, 1.0)
    return max(0, int(raw_damage * mult))


def set_resistance(state: dict[str, Any], damage_type: str, multiplier: float) -> None:
    get_resistances(state)[damage_type] = multiplier
