"""World state management — time, weather, location, and world initialisation.

This is the canonical core world module used by Canon Engine.
All state is mutated in-place; the same dict is returned for chaining.
"""

from __future__ import annotations

import random as _random
from typing import Any

# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------

WEATHER_TYPES: list[str] = [
    "clear", "cloudy", "rain", "heavy_rain", "storm", "fog", "snow",
]

WEATHER_ICONS: dict[str, str] = {
    "clear": "☀️",
    "cloudy": "☁️",
    "rain": "🌧️",
    "heavy_rain": "🌧️",
    "storm": "⛈️",
    "fog": "🌫️",
    "snow": "❄️",
}

# How many game-minutes between mandatory weather churns.
_WEATHER_CHURN_INTERVAL: int = 180

# ---------------------------------------------------------------------------
# Sky / time-of-day
# ---------------------------------------------------------------------------

def _sky_from_minutes(minutes_of_day: int) -> str:
    """Return sky label for a time within a single day (0-1439)."""
    hour = minutes_of_day // 60
    if 5 <= hour < 7:
        return "dawn"
    if 7 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 20:
        return "evening"
    # 20:00 – 04:59
    return "night"


# ---------------------------------------------------------------------------
# ensure_world
# ---------------------------------------------------------------------------

def ensure_world(state: dict[str, Any]) -> dict[str, Any]:
    """Ensure all world keys exist with sane defaults and return the world dict.

    Parameters
    ----------
    state : dict
        The top-level game state dict.  ``state["world"]`` will be created /
        patched in-place.

    Returns
    -------
    dict
        The ``state["world"]`` dict (created if absent).
    """
    w: dict[str, Any] = state.setdefault("world", {})

    # Simple scalar defaults — only set if missing so existing values survive.
    _defaults: dict[str, Any] = {
        "location": "Unknown",
        "location_id": "unknown",
        "minutes_total": 480,  # 8:00 AM day 1
        "weather": "clear",
        "weather_icon": "☀️",
        "sheltered": False,
        "fatigue": 0,
        "location_restable": True,
        "seed": 0,
        "world_id": "",
        "generated": False,
        "procedural_map": {},
        "map": {},
        "lore": "",
    }
    for key, val in _defaults.items():
        w.setdefault(key, val)

    # Nested dict defaults.
    w.setdefault("quests", {"active": {}, "completed": {}, "failed": {}})
    w.setdefault("npcs", {})
    w.setdefault("flags", {})
    w.setdefault("travel_edges", [])

    return w


# ---------------------------------------------------------------------------
# Clock helpers (pure functions that read minutes_total)
# ---------------------------------------------------------------------------

def clock_line(state: dict[str, Any]) -> str:
    """Return ``'Day {day} — {HH:MM}'`` from state."""
    w = state.get("world", {})
    mt = w.get("minutes_total", 480)
    day = mt // 1440 + 1
    tod = mt % 1440
    hh = tod // 60
    mm = tod % 60
    return f"Day {day} — {hh:02d}:{mm:02d}"


def sky(state: dict[str, Any]) -> str:
    """Return sky label for current time."""
    w = state.get("world", {})
    mt = w.get("minutes_total", 480)
    return _sky_from_minutes(mt % 1440)


# ---------------------------------------------------------------------------
# Time advancement
# ---------------------------------------------------------------------------

def advance_world_time(state: dict[str, Any], minutes: int) -> dict[str, Any]:
    """Bump ``minutes_total`` by *minutes*.  Returns the world dict."""
    w = ensure_world(state)
    w["minutes_total"] = w.get("minutes_total", 480) + minutes
    return w


def apply_time_passed(state: dict[str, Any], minutes: int) -> dict[str, Any]:
    """Advance time *and* trigger weather churn every ~180 minutes.

    Weather is re-rolled (using the world seed or a default RNG) whenever the
    accumulated minutes cross a 180-minute boundary.
    """
    w = ensure_world(state)
    old_total = w.get("minutes_total", 480)
    new_total = old_total + minutes
    w["minutes_total"] = new_total

    # Check if we crossed a churn boundary.
    old_bucket = old_total // _WEATHER_CHURN_INTERVAL
    new_bucket = new_total // _WEATHER_CHURN_INTERVAL
    if new_bucket > old_bucket:
        _churn_weather(w)

    return w


def _churn_weather(w: dict[str, Any]) -> None:
    """Re-roll weather, biased toward the current weather."""
    rng = _random.Random(w.get("seed", 0) + w.get("minutes_total", 0))
    # 60 % chance to keep current weather, 40 % to change.
    if rng.random() < 0.4:
        w["weather"] = rng.choice(WEATHER_TYPES)
    w["weather_icon"] = WEATHER_ICONS.get(w["weather"], "❓")


# ---------------------------------------------------------------------------
# Weather display
# ---------------------------------------------------------------------------

def get_weather_display(state: dict[str, Any]) -> dict[str, str]:
    """Return ``{weather, icon, sky}`` for the current world state."""
    w = ensure_world(state)
    return {
        "weather": w.get("weather", "clear"),
        "icon": w.get("weather_icon", WEATHER_ICONS.get(w.get("weather", "clear"), "☀️")),
        "sky": _sky_from_minutes(w.get("minutes_total", 480) % 1440),
    }
