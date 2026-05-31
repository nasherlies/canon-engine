"""Status effects registry, apply/remove, durations, STATUS_REGISTRY for UI."""

from __future__ import annotations

from typing import Any

# Predefined effects — each has duration in turns (0 = permanent until removed)
STATUS_REGISTRY: dict[str, dict[str, Any]] = {
    "poisoned": {"label": "Poisoned", "duration": 3, "damage_per_turn": 2},
    "burning": {"label": "Burning", "duration": 2, "damage_per_turn": 3},
    "frozen": {"label": "Frozen", "duration": 1, "skip_turn": True},
    "stunned": {"label": "Stunned", "duration": 1, "skip_turn": True},
    "haste": {"label": "Haste", "duration": 3, "extra_action": True},
    "blessed": {"label": "Blessed", "duration": 5, "bonus": 2},
    "cursed": {"label": "Cursed", "duration": 5, "penalty": 2},
    "bleeding": {"label": "Bleeding", "duration": 4, "damage_per_turn": 1},
    "shielded": {"label": "Shielded", "duration": 3, "temp_hp": 10},
}


def get_active_effects(state: dict[str, Any]) -> list[dict[str, Any]]:
    return state.setdefault("status_effects", [])


def apply_status(state: dict[str, Any], effect_name: str, duration: int | None = None) -> dict[str, Any]:
    template = STATUS_REGISTRY.get(effect_name)
    if template is None:
        return {"applied": False, "reason": f"Unknown effect: {effect_name}"}
    eff = {**template, "name": effect_name, "remaining": duration or template.get("duration", 1)}
    get_active_effects(state).append(eff)
    return {"applied": True, "effect": eff}


def remove_status(state: dict[str, Any], effect_name: str) -> bool:
    effects = get_active_effects(state)
    for i, e in enumerate(effects):
        if e.get("name") == effect_name:
            effects.pop(i)
            return True
    return False


def tick_statuses(state: dict[str, Any]) -> list[str]:
    """Decrement durations, remove expired. Returns event messages."""
    events = []
    effects = get_active_effects(state)
    keep = []
    for e in effects:
        e["remaining"] = e.get("remaining", 1) - 1
        if e["remaining"] <= 0:
            events.append(f"{e.get('label', e['name'])} has worn off.")
        else:
            keep.append(e)
    state["status_effects"] = keep
    return events
