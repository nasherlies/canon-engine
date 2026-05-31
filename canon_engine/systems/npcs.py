"""NPC registry, sheets, gift/threaten flows."""

from __future__ import annotations

from typing import Any


def get_npc_registry(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return state.setdefault("npcs", {})


def register_npc(state: dict[str, Any], npc: dict[str, Any]) -> None:
    get_npc_registry(state)[npc["name"].lower()] = npc


def get_npc(state: dict[str, Any], name: str) -> dict[str, Any] | None:
    return get_npc_registry(state).get(name.lower())


def handle_talk(state: dict[str, Any], npc_name: str) -> dict[str, Any]:
    npc = get_npc(state, npc_name)
    if npc is None:
        return {"narration": f"There's nobody called '{npc_name}' here."}
    return {"narration": f"{npc['name']} regards you. (dialogue stub)", "npc": npc}


def gift_npc(state: dict[str, Any], npc_name: str, item_name: str) -> dict[str, Any]:
    return {"narration": f"You offer {item_name} to {npc_name}."}


def threaten_npc(state: dict[str, Any], npc_name: str) -> dict[str, Any]:
    return {"narration": f"You threaten {npc_name}."}
