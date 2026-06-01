"""Canon Engine — Underworld / Soul System

Soul system for dead characters: enter the underworld as a soul blob,
lose memories over time, and eventually return to life.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Enter / Exit Underworld
# ---------------------------------------------------------------------------

def enter_underworld(state: dict[str, Any]) -> dict[str, Any]:
    """Create a soul blob for a dead character entering the underworld.

    Preserves key stats as a soul representation. Sets underworld status.

    Returns {ok, message, soul}.
    """
    player = state.get("player", state)

    # Create soul blob — a stripped-down copy of the character
    soul = {
        "name": player.get("name", "Unknown"),
        "level": player.get("level", 1),
        "stats": dict(player.get("stats", {})),
        "gold": 0,  # souls carry no gold
        "memories": list(state.get("world_log", [])[-10:]),  # last 10 memories
        "soul_fragments": 100,  # degrades over time
        "turns_in_underworld": 0,
    }

    state["underworld"] = {
        "active": True,
        "soul": soul,
        "entry_turn": state.get("turn", 0),
    }
    state["alive"] = False
    player["alive"] = False

    return {
        "ok": True,
        "message": f"The soul of {soul['name']} drifts into the underworld...",
        "soul": soul,
    }


def exit_underworld(state: dict[str, Any]) -> dict[str, Any]:
    """Return from the underworld to life.

    Restores alive status, clears underworld state.

    Returns {ok, message, fragments_remaining}.
    """
    uw = state.get("underworld", {})
    soul = uw.get("soul", {})
    fragments = soul.get("soul_fragments", 0)

    state["alive"] = True
    player = state.get("player", state)
    player["alive"] = True

    # Clear underworld
    state["underworld"] = {"active": False, "soul": None}

    return {
        "ok": True,
        "message": "You claw your way back from the underworld, reborn into the living world.",
        "fragments_remaining": fragments,
    }


# ---------------------------------------------------------------------------
# Soul sheet
# ---------------------------------------------------------------------------

def soul_sheet(state: dict[str, Any]) -> str:
    """Display the soul's status in the underworld."""
    uw = state.get("underworld", {})
    if not uw.get("active", False):
        return "You are not in the underworld."

    soul = uw.get("soul", {})
    name = soul.get("name", "Unknown")
    level = soul.get("level", 1)
    fragments = soul.get("soul_fragments", 0)
    turns = soul.get("turns_in_underworld", 0)
    memories = soul.get("memories", [])

    lines = [
        f"**═══ Soul of {name} ═══**",
        f"Level: {level}",
        f"Soul Fragments: {fragments}%",
        f"Turns in Underworld: {turns}",
        "",
        "**Memories (fading):**",
    ]

    if memories:
        for mem in memories[-5:]:
            lines.append(f"  - {mem}")
    else:
        lines.append("  (no memories)")

    if fragments <= 25:
        lines.append("")
        lines.append("⚠️ *Your soul is fading rapidly...*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Erosion
# ---------------------------------------------------------------------------

def underworld_erosion_tick(state: dict[str, Any]) -> dict[str, Any]:
    """Tick underworld erosion — lose memories and soul fragments over time.

    Called periodically while the character is in the underworld.
    Each tick: -5 to -15 soul fragments, may lose oldest memory.

    Returns {fragments, memory_lost, message}.
    """
    import random as _random

    uw = state.get("underworld", {})
    if not uw.get("active", False):
        return {"ok": False, "message": "Not in the underworld."}

    soul = uw.get("soul", {})
    fragments = soul.get("soul_fragments", 100)
    turns = soul.get("turns_in_underworld", 0) + 1
    soul["turns_in_underworld"] = turns

    # Erosion: 5-15 fragments per tick
    erosion = _random.randint(5, 15)
    fragments = max(0, fragments - erosion)
    soul["soul_fragments"] = fragments

    # Memory loss — lose oldest memory every 3 turns
    memory_lost = False
    memories = soul.get("memories", [])
    if turns % 3 == 0 and memories:
        memories.pop(0)
        memory_lost = True

    message = f"Soul erodes... ({fragments}% fragments remaining)"
    if memory_lost:
        message += " A memory fades away..."

    if fragments <= 0:
        message += " Your soul has completely faded. Only rebirth can save you now."

    return {
        "ok": True,
        "fragments": fragments,
        "memory_lost": memory_lost,
        "turns": turns,
        "message": message,
    }
