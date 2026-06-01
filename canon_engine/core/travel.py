"""Travel system — move between locations via travel edges.

Travel time is tiered: short (30 min), regional (120 min), continental (480 min).
Edges in ``world["travel_edges"]`` declare connections with an optional ``tier``
key.  Unmatched destinations fall back to ``"short"``.
"""

from __future__ import annotations

import random as _random
from typing import Any

from canon_engine.core.world import apply_time_passed, ensure_world

# Time budgets per tier (game-minutes).
TIER_TIMES: dict[str, int] = {
    "short": 30,
    "regional": 120,
    "continental": 480,
}


def _find_edge(world: dict[str, Any], destination: str) -> dict[str, Any] | None:
    """Return the first travel_edge whose ``to`` matches *destination* (case-insensitive)."""
    dest_lower = destination.lower()
    for edge in world.get("travel_edges", []):
        if edge.get("to", "").lower() == dest_lower:
            return edge
    return None


def apply_engine_travel(
    state: dict[str, Any],
    destination: str,
    rng: _random.Random | None = None,
) -> dict[str, Any]:
    """Move the player to *destination*, apply time and weather churn.

    Parameters
    ----------
    state : dict
        Top-level game state.
    destination : str
        Name or id of the target location.
    rng : random.Random, optional
        Source of randomness.  A fresh instance is created if *None*.

    Returns
    -------
    dict
        ``{narration, destination, time_passed, tier, weather}``
    """
    if rng is None:
        rng = _random.Random()

    w = ensure_world(state)
    edge = _find_edge(w, destination)

    if edge is not None:
        tier = edge.get("tier", "short")
        dest_name = edge.get("to", destination)
        dest_id = edge.get("to_id", destination.lower().replace(" ", "_"))
    else:
        tier = "short"
        dest_name = destination
        dest_id = destination.lower().replace(" ", "_")

    time_cost = TIER_TIMES.get(tier, TIER_TIMES["short"])

    # Apply time + weather churn.
    apply_time_passed(state, time_cost)

    # Update location.
    w["location"] = dest_name
    w["location_id"] = dest_id

    weather = w.get("weather", "clear")
    icon = w.get("weather_icon", "☀️")

    return {
        "narration": (
            f"You travel to {dest_name}. The journey takes {time_cost} minutes "
            f"({tier} distance). You arrive under {weather} skies."
        ),
        "destination": dest_name,
        "time_passed": time_cost,
        "tier": tier,
        "weather": weather,
        "weather_icon": icon,
    }
