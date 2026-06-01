"""
Canon Engine — Companion Banter System

Generates personality-driven companion dialogue reactions to game events.
Banter is loyalty-aware: low loyalty produces sarcastic/dismissive lines,
high loyalty produces supportive/warm lines.

Public API:
    generate_banter(state, event_type, context) -> str

Usage:
    from canon_engine.systems.companion_banter import generate_banter, BanterEvent

    text = generate_banter(game_state, BanterEvent.COMBAT_START, {"enemy": "Goblin"})
    print(text)   # formatted multi-companion banter block
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from canon_engine.systems.companions import (
    Companion,
    PersonalityArchetype,
    get_companions,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BANTER_FILE = Path(__file__).resolve().parents[2] / "content" / "companion_banter.json"


class BanterEvent(str, Enum):
    """All recognised banter trigger events."""
    COMBAT_START = "combat_start"
    ENEMY_KILL = "enemy_kill"
    PLAYER_LOW_HP = "player_low_hp"
    LOOT_FOUND = "loot_found"
    NEW_LOCATION = "new_location"
    REST = "rest"
    PLAYER_DEATH_RISK = "player_death_risk"


# Canonical list for validation / help text
VALID_EVENTS = [e.value for e in BanterEvent]

# How many lines per companion per event
_LINES_PER_BANTER = 2

# Cooldown tracker — prevents the same companion from bantering twice in a row
_last_banter_companion_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

def _load_templates() -> Dict[str, Any]:
    """Load and return the banter template dictionary from JSON."""
    if not _BANTER_FILE.exists():
        raise FileNotFoundError(
            f"Banter content file not found: {_BANTER_FILE}\n"
            "Expected at ~/canon-engine/content/companion_banter.json"
        )
    with open(_BANTER_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("personality", data)


# Cache loaded templates once
_templates: Optional[Dict[str, Any]] = None


def _get_templates() -> Dict[str, Any]:
    global _templates
    if _templates is None:
        _templates = _load_templates()
    return _templates


def reload_templates() -> None:
    """Force-reload templates from disk (useful for hot-reload / testing)."""
    global _templates
    _templates = None


# ---------------------------------------------------------------------------
# Core banter generation
# ---------------------------------------------------------------------------

def _pick_lines(
    personality: str,
    event_type: str,
    loyalty_tier: str,
    n: int = _LINES_PER_BANTER,
) -> List[str]:
    """Pick *n* random template lines for the given personality + event + loyalty."""
    templates = _get_templates()

    persona_data = templates.get(personality, {})
    event_data = persona_data.get(event_type, {})

    # Fall back through loyalty tiers if the exact one is missing
    pool: List[str] = []
    for tier in [loyalty_tier, "medium", "low", "high"]:
        pool = event_data.get(tier, [])
        if pool:
            break

    if not pool:
        return []

    # Pick without replacement (up to available)
    chosen = random.sample(pool, min(n, len(pool)))
    return chosen


def _format_line(line: str, companion: Companion, context: Dict[str, Any]) -> str:
    """Substitute placeholders in a template line."""
    replacements = {
        "{companion}": companion.name,
        "{player}": context.get("player_name", "the hero"),
        "{enemy}": context.get("enemy", "the enemy"),
        "{item}": context.get("item", "something strange"),
        "{location}": context.get("location", "this place"),
    }
    for placeholder, value in replacements.items():
        line = line.replace(placeholder, value)
    return line


def _select_companions(
    companions: List[Optional[Companion]],
    max_speakers: int = 2,
) -> List[Companion]:
    """Choose which companions actually speak (avoids same companion twice)."""
    global _last_banter_companion_id

    available = [c for c in companions if c is not None and c.recruited]
    if not available:
        return []

    # Try to avoid repeating the last speaker
    if _last_banter_companion_id and len(available) > 1:
        available = [c for c in available if c.id != _last_banter_companion_id] or available

    speakers = random.sample(available, min(max_speakers, len(available)))
    if speakers:
        _last_banter_companion_id = speakers[-1].id

    return speakers


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_banter(
    state: Any,
    event_type: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate formatted banter text for the current game state.

    Parameters
    ----------
    state : Any
        The game state object.  If it has a ``companions`` attribute that is a
        list of companion objects, those will be used.  Otherwise, the system
        falls back to :func:`companions.get_companions`.
    event_type : str
        One of the :class:`BanterEvent` values (e.g. ``"combat_start"``).
    context : dict, optional
        Extra placeholders (``player_name``, ``enemy``, ``item``, ``location``)
        substituted into template lines.

    Returns
    -------
    str
        A formatted banter block ready to be inserted into narration.
        Returns an empty string if no companions can banter.
    """
    if context is None:
        context = {}

    # --- Validate event type -----------------------------------------------
    valid_events = {e.value for e in BanterEvent}
    if event_type not in valid_events:
        return (
            f"[Banter Error] Unknown event '{event_type}'. "
            f"Valid events: {', '.join(sorted(valid_events))}"
        )

    # --- Gather active companions ------------------------------------------
    companions: List[Companion] = []
    if hasattr(state, "companions"):
        companions = list(state.companions)
    else:
        companions = get_companions()

    if not companions:
        return ""

    # --- Select speakers (1-2 companions banter per event) -----------------
    max_speakers = min(2, len(companions))
    speakers = _select_companions(companions, max_speakers=max_speakers)
    if not speakers:
        return ""

    # --- Build banter lines ------------------------------------------------
    banter_blocks: List[str] = []

    for companion in speakers:
        loyalty = companion.loyalty_tier
        lines = _pick_lines(companion.personality.value, event_type, loyalty, n=_LINES_PER_BANTER)

        if not lines:
            continue

        formatted = [_format_line(line, companion, context) for line in lines]
        # Format as dialogue with companion name
        dialogue = "\n".join(f"  **{companion.name}:** \"{line}\"" for line in formatted)
        banter_blocks.append(dialogue)

    if not banter_blocks:
        return ""

    return "\n".join(banter_blocks)


# ---------------------------------------------------------------------------
# Convenience wrappers (one-liners for common integration points)
# ---------------------------------------------------------------------------

def on_combat_start(state: Any, enemy: str = "the enemy", **ctx: Any) -> str:
    """Banter when combat begins."""
    return generate_banter(state, BanterEvent.COMBAT_START, {"enemy": enemy, **ctx})


def on_enemy_kill(state: Any, enemy: str = "the enemy", **ctx: Any) -> str:
    """Banter when an enemy is slain."""
    return generate_banter(state, BanterEvent.ENEMY_KILL, {"enemy": enemy, **ctx})


def on_player_low_hp(state: Any, **ctx: Any) -> str:
    """Banter when the player's HP drops critically low."""
    return generate_banter(state, BanterEvent.PLAYER_LOW_HP, ctx)


def on_loot_found(state: Any, item: str = "something strange", **ctx: Any) -> str:
    """Banter when loot is discovered."""
    return generate_banter(state, BanterEvent.LOOT_FOUND, {"item": item, **ctx})


def on_new_location(state: Any, location: str = "this place", **ctx: Any) -> str:
    """Banter when the party arrives at a new location."""
    return generate_banter(state, BanterEvent.NEW_LOCATION, {"location": location, **ctx})


def on_rest(state: Any, **ctx: Any) -> str:
    """Banter when the party rests."""
    return generate_banter(state, BanterEvent.REST, ctx)


def on_player_death_risk(state: Any, **ctx: Any) -> str:
    """Banter when the player is at risk of death."""
    return generate_banter(state, BanterEvent.PLAYER_DEATH_RISK, ctx)


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Canon Engine Companion Banter System — Demo ===\n")

    # Recruit a couple of companions for the demo
    from canon_engine.systems.companions import recruit, seed_defaults

    recruit("korrin")
    recruit("sable")
    recruit("mirael")
    recruit("lyra")

    # Show loyalty tiers
    for c in get_companions():
        print(f"  {c.name} ({c.personality.value}) — loyalty {c.loyalty} [{c.loyalty_tier}]")
    print()

    # Simulate all events
    for event in BanterEvent:
        print(f"--- {event.value} ---")
        result = generate_banter(
            None,
            event.value,
            {"player_name": "Aldric", "enemy": "Shadow Drake", "item": "a glowing amulet", "location": "the Crystal Caverns"},
        )
        print(result)
        print()

    # Show loyalty shift
    print("=== After lowering Korrin's loyalty to 15 ===")
    from canon_engine.systems.companions import get_companion
    korrin = get_companion("korrin")
    korrin.loyalty = 15
    print(f"  {korrin.name} loyalty: {korrin.loyalty} [{korrin.loyalty_tier}]\n")
    print(on_combat_start(None, enemy="Ancient Dragon"))
