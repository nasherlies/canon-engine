"""Companion loyalty, recruit, dismiss, relationship tracking."""

from __future__ import annotations

from typing import Any


def get_companions(state: dict[str, Any]) -> list[dict[str, Any]]:
    return state.setdefault("companions", [])


def recruit(state: dict[str, Any], npc: dict[str, Any]) -> dict[str, Any]:
    """Recruit an NPC as companion. Returns result dict."""
    comp = {"name": npc.get("name", "Unknown"), "loyalty": 0, "stats": npc.get("stats", {})}
    get_companions(state).append(comp)
    return {"narration": f"{comp['name']} joins your party!", "companion": comp}


def dismiss(state: dict[str, Any], name: str) -> dict[str, Any]:
    comps = get_companions(state)
    for i, c in enumerate(comps):
        if c["name"].lower() == name.lower():
            comps.pop(i)
            return {"narration": f"{name} leaves your party."}
    return {"narration": f"No companion named '{name}' found."}


def adjust_loyalty(state: dict[str, Any], name: str, delta: int) -> int:
    """Adjust loyalty (-100 to +100). Returns new loyalty."""
    for c in get_companions(state):
        if c["name"].lower() == name.lower():
            c["loyalty"] = max(-100, min(100, c["loyalty"] + delta))
            return c["loyalty"]
    return 0


def handle_companion_command(state: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    sub = parsed.get("action", "list")
    if sub == "list":
        comps = get_companions(state)
        if not comps:
            return {"narration": "You have no companions."}
        lines = [f"- {c['name']} (loyalty {c['loyalty']})" for c in comps]
        return {"narration": "Companions:\n" + "\n".join(lines)}
    return {"narration": "Unknown companion action."}
