"""Helper utilities for recovery mechanics."""

from __future__ import annotations

from typing import Any


def is_alive(state: dict[str, Any]) -> bool:
    char = state.get("character", state)
    return char.get("hp", 0) > 0


def is_stable(state: dict[str, Any]) -> bool:
    return state.get("death_saves", {}).get("stable", False)


def is_in_underworld(state: dict[str, Any]) -> bool:
    return state.get("in_underworld", False)


def is_permadead(state: dict[str, Any]) -> bool:
    return state.get("permadead", False)


def recovery_status(state: dict[str, Any]) -> str:
    if is_permadead(state):
        return "permadead"
    if is_in_underworld(state):
        return "underworld"
    if not is_alive(state):
        if is_stable(state):
            return "stable"
        return "dying"
    return "alive"
