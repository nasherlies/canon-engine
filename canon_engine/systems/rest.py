"""Nap (short rest) and sleep (long rest), CON-scaled healing."""

from __future__ import annotations

from typing import Any

from canon_engine.systems.character import score_to_modifier


def short_rest(state: dict[str, Any]) -> dict[str, Any]:
    """Short rest — heal CON modifier * 2 (min 1)."""
    char = state.get("character", state)
    con_mod = score_to_modifier(char.get("stats", {}).get("CON", 10))
    heal_amt = max(1, con_mod * 2)
    from canon_engine.systems.character import heal
    actual = heal(state, heal_amt)
    return {"narration": f"After a brief rest you recover {actual} HP.", "healed": actual}


def long_rest(state: dict[str, Any]) -> dict[str, Any]:
    """Long rest — full HP restore, clear short-term conditions."""
    char = state.get("character", state)
    from canon_engine.systems.character import heal
    actual = heal(state, char.get("max_hp", 50))
    # Clear temporary conditions
    from canon_engine.systems.status import get_active_effects
    effects = get_active_effects(state)
    state["status_effects"] = [e for e in effects if e.get("permanent")]
    return {"narration": f"After a full night's sleep you recover {actual} HP and feel refreshed.", "healed": actual}
