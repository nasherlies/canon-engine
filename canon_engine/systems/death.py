"""HP zero pipeline, death saves, underworld states."""

from __future__ import annotations

import random
from typing import Any


def check_death(state: dict[str, Any]) -> bool:
    """Return True if character HP <= 0."""
    char = state.get("character", state)
    return char.get("hp", 1) <= 0


def death_save(state: dict[str, Any]) -> dict[str, Any]:
    """Roll a death save (d20, 10+ succeeds). 3 successes = stable, 3 failures = dead."""
    ds = state.setdefault("death_saves", {"successes": 0, "failures": 0})
    roll = random.randint(1, 20)
    if roll == 20:
        char = state.get("character", state)
        char["hp"] = 1
        state.pop("death_saves", None)
        return {"result": "nat20", "narration": "You surge back to consciousness with 1 HP!"}
    if roll == 1:
        ds["failures"] += 2
    elif roll >= 10:
        ds["successes"] += 1
    else:
        ds["failures"] += 1

    if ds["successes"] >= 3:
        ds["stable"] = True
        return {"result": "stable", "narration": "You stabilise."}
    if ds["failures"] >= 3:
        return {"result": "dead", "narration": "You have died."}
    return {"result": "ongoing", "narration": f"Death save: rolled {roll}. (S:{ds['successes']} F:{ds['failures']})"}


def enter_underworld(state: dict[str, Any]) -> dict[str, Any]:
    state["in_underworld"] = True
    return {"narration": "You awaken in the underworld..."}
