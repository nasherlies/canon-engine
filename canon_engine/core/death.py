"""Canon Engine — Death Saving Throws & Death Mechanics

D&D-style death saves: nat 1 = double fail, nat 20 = stabilize,
10+ = success, else fail. 3 successes = stabilized, 3 failures = death.
Also includes CON save to stay at 1 HP (once per combat).
"""
from __future__ import annotations

import random
from typing import Any

from canon_engine.core.status import apply_status, has_status, remove_status

# ---------------------------------------------------------------------------
# Death saving throws
# ---------------------------------------------------------------------------

def death_save(state: dict[str, Any], rng: random.Random | None = None) -> dict[str, Any]:
    """Roll a death saving throw.

    d20:
    - Natural 1: counts as 2 failures
    - Natural 20: instantly stabilize at 1 HP
    - 10-19: success
    - 2-9: failure

    3 successes = stabilized (conscious at 1 HP)
    3 failures = death

    Returns {roll, result, successes, failures, stabilized, dead}.
    """
    _rng = rng or random.Random()
    roll = _rng.randint(1, 20)

    ds = state.setdefault("death_saves", {"successes": 0, "failures": 0})
    successes = ds.get("successes", 0)
    failures = ds.get("failures", 0)
    stabilized = False
    dead = False

    if roll == 1:
        failures += 2
        result = "critical_fail"
    elif roll == 20:
        # Instantly stabilize
        successes = 3
        stabilized = True
        result = "natural_20"
    elif roll >= 10:
        successes += 1
        result = "success"
    else:
        failures += 1
        result = "fail"

    # Check thresholds
    if successes >= 3:
        stabilized = True
    if failures >= 3:
        dead = True

    # Update state
    ds["successes"] = min(successes, 3)
    ds["failures"] = min(failures, 3)

    if stabilized:
        remove_status(state, "dying")
        state["hp"] = 1
        state["alive"] = True
    if dead:
        state["alive"] = False
        state["hp"] = 0

    return {
        "roll": roll,
        "result": result,
        "successes": min(successes, 3),
        "failures": min(failures, 3),
        "stabilized": stabilized,
        "dead": dead,
    }


# ---------------------------------------------------------------------------
# Trigger death / dying
# ---------------------------------------------------------------------------

def trigger_death(state: dict[str, Any]) -> dict[str, Any]:
    """Set the character to dying status and initialize death saves.

    Returns {status, message}.
    """
    apply_status(state, "dying")
    state["death_saves"] = {"successes": 0, "failures": 0}
    state["hp"] = 0
    state["alive"] = False

    return {
        "status": "dying",
        "message": "You collapse! Death saving throws begin...",
        "death_saves": state["death_saves"],
    }


# ---------------------------------------------------------------------------
# HP zero handler
# ---------------------------------------------------------------------------

def after_hp_zero(state: dict[str, Any], rng: random.Random | None = None) -> dict[str, Any]:
    """Called when HP reaches 0.

    Attempts a CON save vs DC 10 to stay at 1 HP (once per combat).
    If the save fails or was already used this combat, enter dying state.

    Returns {stayed_up, message}.
    """
    _rng = rng or random.Random()

    # Check if already used this combat
    combat = state.get("combat", {})
    if combat.get("last_stand_used", False):
        result = trigger_death(state)
        return {
            "stayed_up": False,
            "message": "You already used your last stand this combat. " + result["message"],
        }

    # CON save vs DC 10
    con_stat = state.get("stats", {}).get("CON", 10)
    con_mod = (con_stat - 10) // 2
    roll = _rng.randint(1, 20)
    total = roll + con_mod

    if total >= 10:
        # Success — stay at 1 HP
        state["hp"] = 1
        state["alive"] = True
        combat["last_stand_used"] = True
        return {
            "stayed_up": True,
            "message": f"Through sheer grit, you stay on your feet at 1 HP! (CON save: {roll}+{con_mod}={total} vs DC 10)",
            "roll": roll,
            "total": total,
        }
    else:
        # Fail — enter dying state
        result = trigger_death(state)
        return {
            "stayed_up": False,
            "message": f"You collapse! (CON save: {roll}+{con_mod}={total} vs DC 10). " + result["message"],
            "roll": roll,
            "total": total,
        }
