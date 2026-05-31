"""Skill trees, unlock, skill points."""

from __future__ import annotations

from typing import Any


def get_skills(state: dict[str, Any]) -> list[str]:
    return state.get("character", state).get("skills", [])


def get_skill_points(state: dict[str, Any]) -> int:
    return state.get("character", state).get("skill_points", 0)


def unlock_skill(state: dict[str, Any], skill_name: str) -> dict[str, Any]:
    char = state.get("character", state)
    if skill_name in char.get("skills", []):
        return {"narration": f"You already know {skill_name}."}
    if char.get("skill_points", 0) <= 0:
        return {"narration": "Not enough skill points."}
    char.setdefault("skills", []).append(skill_name)
    char["skill_points"] -= 1
    return {"narration": f"Skill '{skill_name}' unlocked!"}


def handle_skill_command(state: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    sub = parsed.get("action", "list")
    if sub == "list":
        skills = get_skills(state)
        pts = get_skill_points(state)
        return {"narration": f"Skills: {skills or 'none'}\nSkill points: {pts}"}
    if sub == "unlock":
        return unlock_skill(state, parsed.get("skill", ""))
    return {"narration": "Unknown skill action."}
