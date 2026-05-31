"""Rebirth paths: standard, permanent, ascension, descension, purgatory_negotiated."""

from __future__ import annotations

from typing import Any

REBIRTH_PATHS = ["standard", "permanent", "ascension", "descension", "purgatory_negotiated"]


def rebirth(state: dict[str, Any], path: str = "standard") -> dict[str, Any]:
    """Process rebirth based on chosen path."""
    char = state.get("character", state)

    if path == "standard":
        char["hp"] = char.get("max_hp", 50) // 2
        state.pop("death_saves", None)
        state.pop("in_underworld", None)
        return {"narration": "You are reborn, weakened but alive.", "path": path}

    if path == "permanent":
        state["permadead"] = True
        return {"narration": "Your story ends here. Permanent death.", "path": path}

    if path == "ascension":
        char["hp"] = char.get("max_hp", 50)
        char.setdefault("stats", {})["WIS"] = char.get("stats", {}).get("WIS", 10) + 1
        state.pop("death_saves", None)
        state.pop("in_underworld", None)
        return {"narration": "You ascend, reborn with greater wisdom.", "path": path}

    if path == "descension":
        char["hp"] = char.get("max_hp", 50)
        char.setdefault("stats", {})["STR"] = char.get("stats", {}).get("STR", 10) + 1
        state.pop("death_saves", None)
        state.pop("in_underworld", None)
        return {"narration": "You descend into dark power, reborn stronger.", "path": path}

    if path == "purgatory_negotiated":
        char["hp"] = char.get("max_hp", 50) // 3
        state.pop("death_saves", None)
        state.pop("in_underworld", None)
        state["debt"] = state.get("debt", 0) + 100
        return {"narration": "You negotiate your return... at a cost. Debt: 100.", "path": path}

    return {"narration": f"Unknown rebirth path: {path}", "path": path}
