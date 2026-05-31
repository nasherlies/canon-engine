"""Quest generation from templates, progress tracking, turn-in, fail_expired_quests."""

from __future__ import annotations

from typing import Any


def get_quests(state: dict[str, Any]) -> list[dict[str, Any]]:
    return state.setdefault("quests", [])


def add_quest(state: dict[str, Any], quest: dict[str, Any]) -> dict[str, Any]:
    get_quests(state).append(quest)
    return {"narration": f"New quest accepted: {quest.get('title', 'Unknown')}!"}


def update_quest_progress(state: dict[str, Any], quest_id: str, progress: int = 1) -> dict[str, Any]:
    for q in get_quests(state):
        if q.get("id") == quest_id:
            q["progress"] = q.get("progress", 0) + progress
            return {"narration": f"Quest '{q['title']}' progress: {q['progress']}/{q.get('goal', '?')}"}
    return {"narration": "Quest not found."}


def turn_in_quest(state: dict[str, Any], quest_id: str) -> dict[str, Any]:
    quests = get_quests(state)
    for i, q in enumerate(quests):
        if q.get("id") == quest_id:
            if q.get("progress", 0) >= q.get("goal", 1):
                quests.pop(i)
                reward = q.get("reward", {})
                xp = reward.get("xp", 0)
                state.setdefault("character", {})["xp"] = state.get("character", {}).get("xp", 0) + xp
                return {"narration": f"Quest '{q['title']}' completed! +{xp} XP", "reward": reward}
            return {"narration": f"Quest '{q['title']}' not yet complete."}
    return {"narration": "Quest not found."}


def fail_expired_quests(state: dict[str, Any]) -> list[str]:
    """Remove expired quests. Returns list of failure messages."""
    messages = []
    quests = get_quests(state)
    keep = []
    for q in quests:
        if q.get("expires_turn") and state.get("turn", 0) > q["expires_turn"]:
            messages.append(f"Quest '{q.get('title', '?')}' has expired!")
        else:
            keep.append(q)
    state["quests"] = keep
    return messages


def tick_quests(state: dict[str, Any]) -> list[str]:
    """Called every turn. Returns event strings."""
    return fail_expired_quests(state)


def handle_quest_command(state: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    sub = parsed.get("action", "list")
    if sub == "list":
        quests = get_quests(state)
        if not quests:
            return {"narration": "You have no active quests."}
        lines = [f"- {q.get('title', '?')} ({q.get('progress', 0)}/{q.get('goal', '?')})" for q in quests]
        return {"narration": "Quests:\n" + "\n".join(lines)}
    return {"narration": "Unknown quest action."}
