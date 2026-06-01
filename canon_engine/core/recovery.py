"""Recovery mechanics — nap (short rest) and sleep (long rest).

All functions are self-contained and only depend on standard library + the
core world helpers for time advancement.
"""

from __future__ import annotations

import random as _random
from typing import Any

from canon_engine.core.world import apply_time_passed, ensure_world


# ---------------------------------------------------------------------------
# Nap (short rest)
# ---------------------------------------------------------------------------

def resolve_nap(state: dict[str, Any], rng: _random.Random | None = None) -> dict[str, Any]:
    """Resolve a nap: 1-3 hours, ~15 % HP heal.

    If the current location is **not** restable the nap is restless — the
    character recovers less HP (halved) and receives a warning narration.

    Parameters
    ----------
    state : dict
        Top-level game state.
    rng : random.Random, optional
        Source of randomness.  A fresh instance is created if *None*.

    Returns
    -------
    dict
        ``{narration, hp_healed, time_passed}``
    """
    if rng is None:
        rng = _random.Random()

    w = ensure_world(state)
    player = state.get("player", state)

    # Duration: 60-180 minutes (1-3 hours)
    duration = rng.randint(60, 180)

    # HP calculation.
    max_hp = player.get("max_hp", 100)
    current_hp = player.get("hp", max_hp)
    base_heal = int(max_hp * 0.15)
    restable = w.get("location_restable", True)

    if not restable:
        base_heal = max(1, base_heal // 2)

    hp_healed = min(base_heal, max_hp - current_hp)
    player["hp"] = min(max_hp, current_hp + hp_healed)

    # Advance time with weather churn.
    apply_time_passed(state, duration)

    if restable:
        narration = (
            f"You rest for {duration} minutes and recover {hp_healed} HP. "
            "The brief respite leaves you feeling somewhat refreshed."
        )
    else:
        narration = (
            f"You try to rest for {duration} minutes, but the surroundings "
            f"are unfit for proper rest. You toss and turn, recovering only "
            f"{hp_healed} HP."
        )

    return {
        "narration": narration,
        "hp_healed": hp_healed,
        "time_passed": duration,
    }


# ---------------------------------------------------------------------------
# Sleep (long rest)
# ---------------------------------------------------------------------------

def resolve_sleep(state: dict[str, Any], rng: _random.Random | None = None) -> dict[str, Any]:
    """Resolve a full night's sleep (+480 min, HP fully restored).

    Only succeeds when ``location_restable`` is ``True``.  If the location
    is not restable, the function returns a refusal narration and 0 heal.

    Parameters
    ----------
    state : dict
        Top-level game state.
    rng : random.Random, optional
        Source of randomness (unused for sleep duration, kept for API parity).

    Returns
    -------
    dict
        ``{narration, hp_healed, time_passed}``
    """
    if rng is None:
        rng = _random.Random()

    w = ensure_world(state)
    player = state.get("player", state)

    restable = w.get("location_restable", True)
    if not restable:
        return {
            "narration": (
                "You attempt to sleep, but this location is not safe enough "
                "for a proper rest. Perhaps a nap would be better."
            ),
            "hp_healed": 0,
            "time_passed": 0,
        }

    max_hp = player.get("max_hp", 100)
    current_hp = player.get("hp", max_hp)
    hp_healed = max_hp - current_hp

    player["hp"] = max_hp
    player["fatigue"] = 0

    apply_time_passed(state, 480)

    return {
        "narration": (
            f"You sleep through the night ({480} minutes). "
            f"Your HP is fully restored (+{hp_healed} HP). You awaken feeling "
            "well-rested and ready for the day ahead."
        ),
        "hp_healed": hp_healed,
        "time_passed": 480,
    }
