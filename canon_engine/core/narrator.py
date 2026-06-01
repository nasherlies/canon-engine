"""
Canon Engine — AI Narrator

Generates story text via LLM (OpenAI-compatible API via OpenRouter).
Falls back to offline narration when no API key is available.

Public API:
    narrate_and_apply(state, player_input, *, turn, rng, lock_world_time_from_llm=False) -> dict
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NARRATOR_MIN_INTERVAL_SECONDS: float = 1.25
NARRATOR_MODEL: str = os.getenv("NARRATOR_MODEL", "google/gemini-2.0-flash-001")

# Module-level rate limiter state
_last_call_ts: float = 0.0

# ---------------------------------------------------------------------------
# JSON contract instruction sent to the LLM
# ---------------------------------------------------------------------------

_JSON_INSTRUCTION = """\
You are the AI narrator of a tabletop RPG.  Respond ONLY with valid JSON matching this contract:

{
  "narration": "2-4 sentence story text describing what happens",
  "check": {
    "type": "ability|skill|save",
    "stat": "STR|DEX|INT|CHA|CON|LCK",
    "dc": 12,
    "result": "pass|fail",
    "roll": 15
  },
  "state_updates": {
    "hp_delta": 0,
    "mp_delta": 0,
    "stm_delta": 0,
    "gold_delta": 0,
    "xp_add": 0,
    "inventory_add": [{"name": "item name", "rarity": "common|uncommon|rare|epic|legendary"}],
    "inventory_remove": ["item name"],
    "flag_set": {"key": true},
    "stat_deltas": {"STR": 0, "DEX": 0, "INT": 0, "CHA": 0, "CON": 0, "LCK": 0},
    "stat_points": 0
  },
  "suggested_actions": ["/look", "/do examine the altar", "/say Who are you?"],
  "discovered_lore": {
    "title": "The Lost City",
    "category": "location|character|item|event",
    "description": "Brief lore description"
  },
  "quest_update": {
    "action": "new_quest|progress|complete",
    "id": "quest_id",
    "title": "Quest Title",
    "objectives": ["objective 1", "objective 2"]
  },
  "saga_advance": false
}

Rules:
- "narration" is REQUIRED. All other keys are optional — omit them if not relevant.
- "check" only when the action requires a die roll.
- "state_updates" only when game state actually changes.
- "suggested_actions" should list 2-4 contextually relevant next actions.
- "discovered_lore" only when the player discovers something new.
- "quest_update" only when quest state changes.
- "saga_advance" set to true only when a major story milestone is reached.
- Keep narration concise, vivid, and in second person ("you").
"""

_INTRO_INSTRUCTION = """\
You are the AI narrator of a tabletop RPG.  Generate the opening scene for a new adventure.

Respond ONLY with valid JSON:
{
  "narration": "3-5 sentence atmospheric opening describing where the character begins and what they see/feel",
  "suggested_actions": ["/look", "/do examine surroundings", "/say Is anyone there?"],
  "discovered_lore": {
    "title": "Starting location name",
    "category": "location",
    "description": "Brief description of the starting area"
  }
}

Make the opening vivid and immersive. Set the tone for the genre. Use second person ("you").
"""

_THINK_INSTRUCTION = """\
You are the AI narrator of a tabletop RPG. The player character is having an internal thought/monologue.

Respond ONLY with valid JSON:
{
  "narration": "2-3 sentences of internal monologue, reflecting the character's thoughts, memories, or feelings",
  "suggested_actions": ["/look", "/do act on the thought", "/say Speak aloud"]
}

This is internal — no game state changes, no die rolls. Write in second person ("you think about...").
"""


# ---------------------------------------------------------------------------
# LLM client helpers
# ---------------------------------------------------------------------------

def _get_api_config() -> tuple[Optional[str], str]:
    """Return (api_key, base_url). api_key is None if no key is set."""
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, ""

    # OpenRouter base URL if using OPENROUTER key
    if os.getenv("OPENROUTER_API_KEY"):
        base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    else:
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    return api_key, base_url


def _call_llm(system_prompt: str, user_message: str, api_key: str, base_url: str) -> dict:
    """Call the LLM and return parsed JSON response."""
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed; using fallback narration")
        return {}

    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        response = client.chat.completions.create(
            model=NARRATOR_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
            max_tokens=1024,
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

def _build_system_prompt(state: dict, player_input: str) -> str:
    """Build the full system prompt from game state."""
    parts: List[str] = []

    # World bible
    world_bible = state.get("world_bible", "")
    if world_bible:
        parts.append(f"=== WORLD SETTING ===\n{world_bible}")

    # Memory summary (from memory_warm module)
    try:
        from canon_engine.core.memory_warm import get_memory_prompt_block
        memory_block = get_memory_prompt_block(state)
        if memory_block:
            parts.append(f"=== STORY SO FAR ===\n{memory_block}")
    except ImportError:
        pass

    # Quest prompt block
    quests = state.get("quests", {})
    if isinstance(quests, list): quests = {"active": {}, "completed": {}, "failed": {}}
    active_quests = [q for q in quests.get("active", []) if q]
    if active_quests:
        quest_lines = ["=== ACTIVE QUESTS ==="]
        for q in active_quests:
            quest_lines.append(f"- {q.get('title', 'Unknown Quest')}: {', '.join(q.get('objectives', []))}")
        parts.append("\n".join(quest_lines))

    # Saga block
    saga = state.get("saga", {})
    if saga.get("title"):
        parts.append(f"=== CURRENT SAGA ===\n{saga.get('title', '')}: {saga.get('summary', '')}")

    # Recent command log (last 5 entries)
    command_log = state.get("command_log", [])
    recent = command_log[-5:] if command_log else []
    if recent:
        log_lines = ["=== RECENT EVENTS ==="]
        for entry in recent:
            log_lines.append(f"- {entry}")
        parts.append("\n".join(log_lines))

    # Player context
    player = state.get("player", {})
    if player:
        player_info = [f"=== PLAYER ==="]
        player_info.append(f"Name: {player.get('name', 'Unknown')}")
        player_info.append(f"Archetype: {player.get('archetype', 'Adventurer')}")
        player_info.append(f"Race: {player.get('race', 'Human')}")
        stats = player.get("stats", {})
        if stats:
            stat_str = ", ".join(f"{k}:{v}" for k, v in stats.items())
            player_info.append(f"Stats: {stat_str}")
        player_info.append(f"HP: {player.get('hp', 0)}/{player.get('max_hp', 0)}")
        player_info.append(f"Level: {player.get('level', 1)}")
        player_info.append(f"XP: {player.get('xp', 0)}")
        player_info.append(f"Gold: {player.get('gold', 0)}")
        parts.append("\n".join(player_info))

    # Location
    location = state.get("location", "")
    if location:
        parts.append(f"=== CURRENT LOCATION ===\n{location}")

    # Inventory summary
    inventory = state.get("inventory", [])
    if inventory:
        inv_names = [item.get("name", str(item)) if isinstance(item, dict) else str(item) for item in inventory[:20]]
        parts.append(f"=== INVENTORY (top items) ===\n{', '.join(inv_names)}")

    # Genre/tone
    tone = state.get("tone", "")
    genre = state.get("genre", "")
    if tone or genre:
        parts.append(f"=== NARRATIVE STYLE ===\nGenre: {genre}\nTone: {tone}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Validation / normalization
# ---------------------------------------------------------------------------

def _validate_result(raw: dict) -> dict:
    """Validate and normalize narrator JSON response."""
    if not isinstance(raw, dict):
        return {
            "narration": "The world shifts around you, but the details blur.",
            "check": None,
            "state_updates": {},
            "suggested_actions": ["/look"],
            "xp_add": 0,
            "discovered_lore": None,
            "quest_update": None,
            "saga_advance": False,
        }

    result: Dict[str, Any] = {}

    # narration (required)
    result["narration"] = str(raw.get("narration", "The story continues..."))

    # check (optional)
    check = raw.get("check")
    if isinstance(check, dict) and check:
        result["check"] = {
            "type": str(check.get("type", "ability")),
            "stat": str(check.get("stat", "STR")),
            "dc": int(check.get("dc", 10)),
            "result": str(check.get("result", "fail")),
            "roll": int(check.get("roll", 0)),
        }
    else:
        result["check"] = None

    # state_updates (optional)
    su = raw.get("state_updates")
    if isinstance(su, dict) and su:
        updates: Dict[str, Any] = {}
        for key in ("hp_delta", "mp_delta", "stm_delta", "gold_delta"):
            if key in su:
                try:
                    updates[key] = int(su[key])
                except (ValueError, TypeError):
                    updates[key] = 0
        if "xp_add" in su:
            try:
                updates["xp_add"] = int(su["xp_add"])
            except (ValueError, TypeError):
                updates["xp_add"] = 0
        if "inventory_add" in su and isinstance(su["inventory_add"], list):
            normalized_items = []
            for item in su["inventory_add"]:
                if isinstance(item, dict):
                    normalized_items.append({
                        "name": str(item.get("name", "Unknown Item")),
                        "rarity": str(item.get("rarity", "common")),
                    })
                elif isinstance(item, str):
                    normalized_items.append({"name": item, "rarity": "common"})
            updates["inventory_add"] = normalized_items
        if "inventory_remove" in su and isinstance(su["inventory_remove"], list):
            updates["inventory_remove"] = [str(name) for name in su["inventory_remove"]]
        if "flag_set" in su and isinstance(su["flag_set"], dict):
            updates["flag_set"] = su["flag_set"]
        if "stat_deltas" in su and isinstance(su["stat_deltas"], dict):
            updates["stat_deltas"] = {str(k): int(v) for k, v in su["stat_deltas"].items()}
        if "stat_points" in su:
            try:
                updates["stat_points"] = int(su["stat_points"])
            except (ValueError, TypeError):
                updates["stat_points"] = 0
        result["state_updates"] = updates
    else:
        result["state_updates"] = {}

    # xp_add (top-level convenience)
    result["xp_add"] = int(raw.get("xp_add", 0))

    # suggested_actions
    sa = raw.get("suggested_actions")
    if isinstance(sa, list):
        result["suggested_actions"] = [str(a) for a in sa[:6]]
    else:
        result["suggested_actions"] = []

    # discovered_lore
    lore = raw.get("discovered_lore")
    if isinstance(lore, dict) and lore:
        result["discovered_lore"] = {
            "title": str(lore.get("title", "Unknown")),
            "category": str(lore.get("category", "misc")),
            "description": str(lore.get("description", "")),
        }
    else:
        result["discovered_lore"] = None

    # quest_update
    qu = raw.get("quest_update")
    if isinstance(qu, dict) and qu:
        result["quest_update"] = {
            "action": str(qu.get("action", "progress")),
            "id": str(qu.get("id", "unknown")),
            "title": str(qu.get("title", "")),
            "objectives": [str(o) for o in qu.get("objectives", [])],
        }
    else:
        result["quest_update"] = None

    # saga_advance
    result["saga_advance"] = bool(raw.get("saga_advance", False))

    return result


# ---------------------------------------------------------------------------
# Offline fallback narrators
# ---------------------------------------------------------------------------

def _fallback_intro(state: dict) -> dict:
    """Generate an offline intro when no API key is available."""
    player = state.get("player", {})
    name = player.get("name", "Adventurer")
    archetype = player.get("archetype", "wanderer")
    location = state.get("location", "a crossroads")
    genre = state.get("genre", "fantasy")

    narration = (
        f"You are {name}, a {archetype} of modest renown. "
        f"The air is thick with possibility as you stand at {location}. "
        f"Your journey begins here — the world stretches before you, vast and unknown. "
        f"What will you do first?"
    )

    return {
        "narration": narration,
        "check": None,
        "state_updates": {},
        "suggested_actions": ["/look", "/do examine your surroundings", "/say What is this place?"],
        "xp_add": 0,
        "discovered_lore": {
            "title": location if isinstance(location, str) else "The Beginning",
            "category": "location",
            "description": f"The starting point of {name}'s adventure.",
        },
        "quest_update": None,
        "saga_advance": False,
    }


def _fallback_narration(state: dict, player_input: str) -> dict:
    """Generate offline narration when no API key is available."""
    location = state.get("location", "an unknown place")
    player = state.get("player", {})
    name = player.get("name", "the adventurer")

    narration = (
        f"{name} considers their next move at {location}. "
        f"The world reacts subtly to the action taken — "
        f"though the full details remain shrouded in mystery."
    )

    suggested = ["/look", "/do investigate further", "/say Something feels off"]
    if "attack" in player_input.lower() or "fight" in player_input.lower():
        suggested = ["/look enemies", "/attack", "/flee"]
    elif "look" in player_input.lower():
        suggested = ["/do examine closely", "/do move forward", "/say What do I see?"]

    return {
        "narration": narration,
        "check": None,
        "state_updates": {},
        "suggested_actions": suggested,
        "xp_add": 0,
        "discovered_lore": None,
        "quest_update": None,
        "saga_advance": False,
    }


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

def _enforce_rate_limit() -> None:
    """Block until NARRATOR_MIN_INTERVAL_SECONDS have elapsed since last call."""
    global _last_call_ts
    now = time.monotonic()
    elapsed = now - _last_call_ts
    if elapsed < NARRATOR_MIN_INTERVAL_SECONDS:
        import time as _time
        _time.sleep(NARRATOR_MIN_INTERVAL_SECONDS - elapsed)
    _last_call_ts = time.monotonic()


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def narrate_and_apply(
    state: dict,
    player_input: str,
    *,
    turn: int = 0,
    rng: Any = None,
    lock_world_time_from_llm: bool = False,
) -> dict:
    """
    Generate narration for a player action and return the parsed result.

    Parameters
    ----------
    state : dict
        The full game state.
    player_input : str
        The raw player input / command text.
    turn : int
        Current turn number.
    rng : random.Random, optional
        Seeded RNG (unused by narrator directly, available for extensions).
    lock_world_time_from_llm : bool
        If True, the LLM's time suggestions override state time.

    Returns
    -------
    dict
        Validated narrator result matching the JSON contract.
    """
    # Determine instruction mode
    is_intro = player_input.strip() in ("__intro__", "/intro")
    is_think = player_input.strip().startswith("/think") or player_input.strip().startswith("think ")

    # Build system prompt
    if is_intro:
        system_prompt = _INTRO_INSTRUCTION
    elif is_think:
        system_prompt = _THINK_INSTRUCTION
    else:
        system_prompt = _JSON_INSTRUCTION + "\n\n" + _build_system_prompt(state, player_input)

    # Try LLM path
    api_key, base_url = _get_api_config()
    if api_key:
        _enforce_rate_limit()
        raw = _call_llm(system_prompt, player_input, api_key, base_url)
        if raw:
            result = _validate_result(raw)
            return result

    # Offline fallback
    if is_intro:
        result = _fallback_intro(state)
    else:
        result = _fallback_narration(state, player_input)
    return _validate_result(result)
