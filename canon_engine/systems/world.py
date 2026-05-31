"""World state, time management, weather, location management."""

from __future__ import annotations

from typing import Any

# Minutes per game-turn for various actions
ACTION_TIME = {"move": 10, "rest": 30, "sleep": 480, "scout": 15, "default": 5}


def get_world(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault("world", {"minutes_total": 480, "weather": "clear", "location": "unknown"})


def advance_world_time(state: dict[str, Any], minutes: int) -> dict[str, Any]:
    """Advance the world clock. Returns time info dict."""
    w = get_world(state)
    w["minutes_total"] = w.get("minutes_total", 0) + minutes
    return {"total_minutes": w["minutes_total"], "added": minutes}


def apply_time_passed(state: dict[str, Any], parsed: dict[str, Any]) -> int:
    """Apply default time cost for a parsed command. Returns minutes added."""
    kind = parsed.get("kind", "default")
    minutes = ACTION_TIME.get(kind, ACTION_TIME["default"])
    advance_world_time(state, minutes)
    return minutes


def describe_location(state: dict[str, Any]) -> str:
    w = get_world(state)
    loc = w.get("location", "an unknown place")
    weather = w.get("weather", "clear")
    hours = (w.get("minutes_total", 0) % 1440) // 60
    return f"You are at {loc}. The weather is {weather}. It is hour {hours} of the day."


def move_player(state: dict[str, Any], direction: str) -> dict[str, Any]:
    """Move the player in a direction. Returns result dict."""
    w = get_world(state)
    current = w.get("location", "unknown")
    # Stub: just acknowledge the move
    new_loc = f"{current}/{direction}"
    w["location"] = new_loc
    return {"narration": f"You travel {direction} and arrive at {new_loc}.", "layout": {"location": new_loc}}
