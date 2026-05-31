"""Saga framework, spine/pods, advance validation."""

from __future__ import annotations

from typing import Any


def get_saga(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault("saga", {"spine": [], "pods": [], "current_step": 0})


def advance_saga(state: dict[str, Any]) -> dict[str, Any]:
    """Advance to next saga step if validation passes."""
    saga = get_saga(state)
    step = saga.get("current_step", 0)
    spine = saga.get("spine", [])
    if step >= len(spine):
        return {"narration": "The saga has reached its conclusion.", "advanced": False}
    current = spine[step]
    if not validate_saga_step(state, current):
        return {"narration": f"You cannot advance yet: {current.get('blocker', 'requirements not met')}", "advanced": False}
    saga["current_step"] = step + 1
    return {"narration": f"Saga advances: {current.get('title', 'Next chapter')}", "advanced": True}


def validate_saga_step(state: dict[str, Any], step: dict[str, Any]) -> bool:
    """Check if prerequisites for a saga step are met."""
    reqs = step.get("requires", [])
    completed = state.get("completed_quests", set())
    return all(r in completed for r in reqs)


def add_saga_pod(state: dict[str, Any], pod: dict[str, Any]) -> None:
    get_saga(state).setdefault("pods", []).append(pod)
