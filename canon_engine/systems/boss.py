"""Boss phases, special hooks on defeat."""

from __future__ import annotations

from typing import Any, Callable


def get_boss_state(state: dict[str, Any]) -> dict[str, Any] | None:
    return state.get("boss")


def check_phase_transition(state: dict[str, Any]) -> str | None:
    """Check if boss HP crossed a phase threshold. Returns new phase or None."""
    boss = get_boss_state(state)
    if boss is None:
        return None
    enemy = boss.get("enemy", {})
    hp_pct = enemy.get("hp", 0) / max(1, enemy.get("max_hp", 1))
    thresholds = boss.get("phase_thresholds", [0.5, 0.25])
    current_phase = boss.get("current_phase", 0)
    for i, t in enumerate(thresholds):
        if hp_pct <= t and current_phase <= i:
            boss["current_phase"] = i + 1
            return f"phase_{i + 1}"
    return None


def on_boss_defeat(state: dict[str, Any]) -> dict[str, Any]:
    """Called when boss HP reaches 0. Returns reward/event dict."""
    boss = get_boss_state(state)
    if boss is None:
        return {"narration": "No boss to defeat."}
    reward = boss.get("reward", {})
    boss["defeated"] = True
    return {"narration": f"The boss {boss.get('enemy', {}).get('name', 'Unknown')} has been vanquished!", "reward": reward}
