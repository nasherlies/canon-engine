"""Scout/stealth/detect/disarm."""

from __future__ import annotations

import random
from typing import Any


def scout_area(state: dict[str, Any]) -> dict[str, Any]:
    """Scout the current area for threats/items."""
    roll = random.randint(1, 20)
    dex_mod = (state.get("character", state).get("stats", {}).get("DEX", 10) - 10) // 2
    total = roll + dex_mod
    if total >= 15:
        return {"narration": f"You carefully survey the area and spot details others would miss. (rolled {roll}+{dex_mod})"}
    return {"narration": f"You glance around but notice nothing special. (rolled {roll}+{dex_mod})"}


def attempt_stealth(state: dict[str, Any]) -> dict[str, Any]:
    roll = random.randint(1, 20)
    dex_mod = (state.get("character", state).get("stats", {}).get("DEX", 10) - 10) // 2
    state["stealth_roll"] = roll + dex_mod
    return {"narration": f"You attempt to hide. (rolled {roll}+{dex_mod})", "total": roll + dex_mod}


def attempt_detect(state: dict[str, Any]) -> dict[str, Any]:
    roll = random.randint(1, 20)
    wis_mod = (state.get("character", state).get("stats", {}).get("WIS", 10) - 10) // 2
    return {"narration": f"You scan for hidden things. (rolled {roll}+{wis_mod})", "total": roll + wis_mod}


def attempt_disarm(state: dict[str, Any], trap: dict[str, Any] | None = None) -> dict[str, Any]:
    roll = random.randint(1, 20)
    dex_mod = (state.get("character", state).get("stats", {}).get("DEX", 10) - 10) // 2
    dc = (trap or {}).get("dc", 12)
    total = roll + dex_mod
    if total >= dc:
        return {"narration": f"You disarm the trap! (rolled {roll}+{dex_mod} vs DC {dc})", "success": True}
    return {"narration": f"Failed to disarm! (rolled {roll}+{dex_mod} vs DC {dc})", "success": False}
