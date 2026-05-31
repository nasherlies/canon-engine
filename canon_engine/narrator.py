"""Narrator – the AI storyteller for Canon Engine.

The narrator is the bridge between player input and game state.  It:

1. Assembles a rich system prompt from the world bible, memory stack, saga
   framework, character sheet, and companion roster.
2. Sends the prompt plus recent dialogue to an OpenAI-compatible LLM.
3. Parses the LLM's response into structured narration, optional state
   updates, and optional UI layout hints.

Public API
----------
* ``NarratorResponse`` – typed dataclass for LLM narration output.
* ``narrate(state, player_input, *, premium=False) -> NarratorResponse``
* ``build_system_prompt(state) -> str``
* ``parse_narration(raw_text) -> NarratorResponse``
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from canon_engine.constants import ENGINE_NAME, MAX_NARRATIVE_TOKENS
from canon_engine.memory import get_memory_context
from canon_engine.openai_client import chat_completion, resolve_model

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: JSON block delimiters the LLM is asked to use for structured data.
_STATE_BLOCK_START: str = "<<<STATE_UPDATE>>>"
_STATE_BLOCK_END: str = "<<<END_STATE_UPDATE>>>"

_LAYOUT_BLOCK_START: str = "<<<LAYOUT>>>"
_LAYOUT_BLOCK_END: str = "<<<END_LAYOUT>>>"

#: How many recent world-log entries to pass as dialogue history.
_HISTORY_LIMIT: int = 10


# ---------------------------------------------------------------------------
# Response dataclass
# ---------------------------------------------------------------------------


@dataclass
class NarratorResponse:
    """Structured output from a narration call.

    Attributes
    ----------
    narration : str
        The narrative text shown to the player.
    state_updates : dict or None
        A partial state dict that the caller should merge into the live
        state.  ``None`` when the LLM produced no state changes.
    layout : dict or None
        Optional UI layout hints (e.g. ``{"panel": "combat", "highlight":
        "critical_hit"}``).  ``None`` when the LLM produced none.
    raw_text : str
        The unmodified LLM output (useful for debugging / logging).
    model : str
        The model that produced this response.
    """

    narration: str
    state_updates: Optional[Dict[str, Any]] = None
    layout: Optional[Dict[str, Any]] = None
    raw_text: str = ""
    model: str = ""


# ---------------------------------------------------------------------------
# System prompt assembly
# ---------------------------------------------------------------------------


def _format_world_bible(world_bible: Dict[str, Any]) -> str:
    """Render the world bible dict into a prompt-friendly text block.

    The world bible is a dict of ``{topic: content}`` pairs.  Each entry
    is rendered as a numbered heading.
    """
    if not world_bible:
        return ""

    lines: List[str] = ["## World Bible"]
    for i, (topic, content) in enumerate(world_bible.items(), 1):
        lines.append(f"{i}. **{topic}**: {content}")
    return "\n".join(lines)


def _format_character_sheet(player: Dict[str, Any]) -> str:
    """Render the player character's key attributes."""
    if not player:
        return ""

    lines: List[str] = ["## Player Character"]
    name = player.get("name", "Unknown")
    lines.append(f"- **Name**: {name}")

    # Core stats (if present).
    for key in ("class", "race", "level", "hp", "max_hp", "mp", "max_mp",
                "str", "dex", "int", "cha", "con", "lck",
                "STR", "DEX", "INT", "CHA", "CON", "LCK"):
        if key in player:
            lines.append(f"- **{key.upper()}**: {player[key]}")

    # Location
    location = player.get("location")
    if location:
        lines.append(f"- **Location**: {location}")

    return "\n".join(lines)


def _format_companions(companions: Sequence[Any]) -> str:
    """Render companion roster for the prompt."""
    if not companions:
        return ""

    lines: List[str] = ["## Companions"]
    for comp in companions:
        if isinstance(comp, dict):
            name = comp.get("name", "Unknown")
            status = comp.get("status", "active")
            loyalty = comp.get("loyalty", "?")
            lines.append(f"- **{name}** (status={status}, loyalty={loyalty})")
        else:
            lines.append(f"- {comp}")
    return "\n".join(lines)


def _format_saga(saga: Sequence[Any]) -> str:
    """Render the clipped SAGA_FRAMEWORK block.

    The saga is a list of arc descriptors.  Each may be a plain string
    or a dict with ``"title"``, ``"status"``, and ``"summary"`` keys.
    Only the current and next arcs are injected to save tokens.
    """
    if not saga:
        return ""

    lines: List[str] = ["## Saga Framework (Current Arc)"]
    # Show the last (most recent) entry and the next one if available.
    entries = list(saga)
    current = entries[-1] if entries else None
    upcoming = entries[-2] if len(entries) >= 2 else None

    def _render_arc(arc: Any, label: str) -> None:
        if isinstance(arc, dict):
            title = arc.get("title", arc.get("name", "Untitled"))
            status = arc.get("status", "active")
            summary = arc.get("summary", arc.get("description", ""))
            lines.append(f"**{label}: {title}** (status={status})")
            if summary:
                lines.append(summary)
        elif isinstance(arc, str):
            lines.append(f"**{label}**: {arc}")

    if upcoming:
        _render_arc(upcoming, "Previous Arc")
        lines.append("")
    if current:
        _render_arc(current, "Current Arc")

    return "\n".join(lines)


def build_system_prompt(state: Dict[str, Any]) -> str:
    """Assemble the full system prompt from all state components.

    Parameters
    ----------
    state : dict
        The current game state.

    Returns
    -------
    str
        A complete system prompt string.
    """
    parts: List[str] = []

    # ── Role instruction ──────────────────────────────────────────────
    parts.append(
        f"You are the narrator of {ENGINE_NAME}, an AI-powered text-based "
        "infinite RPG.  You describe the world, role-play every NPC, and "
        "drive the story forward in response to the player's actions.\n\n"
        "Rules:\n"
        "- Stay in character as the narrator (second-person perspective).\n"
        "- Be vivid but concise; keep responses under 300 words unless the "
        "scene demands more.\n"
        "- Never break the fourth wall or reference game mechanics unless "
        "the player explicitly asks for stats.\n"
        "- When the player's action has mechanical consequences (damage, "
        "item loss, stat change), include a STATE_UPDATE block.\n"
        "- Keep world bible lore consistent.  If a contradiction arises, "
        "prioritise the world bible."
    )

    # ── World Bible ───────────────────────────────────────────────────
    bible_text = _format_world_bible(state.get("world_bible", {}))
    if bible_text:
        parts.append(bible_text)

    # ── Character sheet ───────────────────────────────────────────────
    char_text = _format_character_sheet(state.get("player", {}))
    if char_text:
        parts.append(char_text)

    # ── Companions ────────────────────────────────────────────────────
    comp_text = _format_companions(state.get("companions", []))
    if comp_text:
        parts.append(comp_text)

    # ── Saga Framework ────────────────────────────────────────────────
    saga_text = _format_saga(state.get("saga", []))
    if saga_text:
        parts.append(saga_text)

    # ── Memory ────────────────────────────────────────────────────────
    memory_text = get_memory_context(state)
    if memory_text:
        parts.append(memory_text)

    # ── Structured-output instructions ────────────────────────────────
    parts.append(
        "## Response Format\n"
        "After your narration, if the player's action changes game state, "
        "include a JSON block wrapped in these exact delimiters:\n"
        f"{_STATE_BLOCK_START}\n"
        '{{ "player": {{"hp": 42}}, "world_log": ["<new log entry>"] }}\n'
        f"{_STATE_BLOCK_END}\n\n"
        "Only include fields that changed.  Omit the block entirely if "
        "nothing changed.\n\n"
        "Optionally, include a layout hint:\n"
        f"{_LAYOUT_BLOCK_START}\n"
        '{{ "panel": "combat", "highlight": "critical_hit" }}\n'
        f"{_LAYOUT_BLOCK_END}"
    )

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Dialogue history
# ---------------------------------------------------------------------------


def _build_history(
    state: Dict[str, Any],
    player_input: str,
    *,
    limit: int = _HISTORY_LIMIT,
) -> List[Dict[str, str]]:
    """Build the messages array (system + recent history + current turn).

    Returns
    -------
    list of dict
        OpenAI-style messages list.
    """
    messages: List[Dict[str, str]] = []

    # System prompt.
    messages.append({"role": "system", "content": build_system_prompt(state)})

    # Recent world log as assistant/user turns (alternating).
    world_log = state.get("world_log", [])
    if world_log:
        recent = world_log[-limit:]
        for i, entry in enumerate(recent):
            text = entry if isinstance(entry, str) else (
                entry.get("text") or entry.get("content") or json.dumps(entry)
            )
            # Even-indexed entries are narrator (assistant), odd are player.
            # This is a heuristic; the world log may alternate.
            role = "assistant" if i % 2 == 0 else "user"
            messages.append({"role": role, "content": text})

    # Current player input.
    messages.append({"role": "user", "content": player_input})

    return messages


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _extract_json_block(text: str, start: str, end: str) -> Optional[Dict[str, Any]]:
    """Extract and parse a JSON block delimited by *start* and *end* markers.

    Returns
    -------
    dict or None
        Parsed JSON dict, or ``None`` if the block is absent or invalid.
    """
    pattern = re.escape(start) + r"\s*(\{.*?\})\s*" + re.escape(end)
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None

    raw_json = match.group(1).strip()
    try:
        parsed = json.loads(raw_json)
        if isinstance(parsed, dict):
            return parsed
        logger.warning("Parsed JSON block is not a dict: %s", type(parsed).__name__)
        return None
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse JSON block: %s", exc)
        return None


def _strip_blocks(text: str) -> str:
    """Remove all delimited blocks from the narration text."""
    # Remove state-update blocks.
    text = re.sub(
        re.escape(_STATE_BLOCK_START) + r".*?" + re.escape(_STATE_BLOCK_END),
        "",
        text,
        flags=re.DOTALL,
    )
    # Remove layout blocks.
    text = re.sub(
        re.escape(_LAYOUT_BLOCK_START) + r".*?" + re.escape(_LAYOUT_BLOCK_END),
        "",
        text,
        flags=re.DOTALL,
    )
    return text.strip()


def parse_narration(raw_text: str, *, model: str = "") -> NarratorResponse:
    """Parse a raw LLM response into a structured ``NarratorResponse``.

    Parameters
    ----------
    raw_text : str
        The full text returned by the LLM.
    model : str
        The model name (stored for debugging).

    Returns
    -------
    NarratorResponse
        Parsed response with narration, optional state_updates, and layout.
    """
    state_updates = _extract_json_block(raw_text, _STATE_BLOCK_START, _STATE_BLOCK_END)
    layout = _extract_json_block(raw_text, _LAYOUT_BLOCK_START, _LAYOUT_BLOCK_END)
    narration = _strip_blocks(raw_text)

    return NarratorResponse(
        narration=narration,
        state_updates=state_updates,
        layout=layout,
        raw_text=raw_text,
        model=model,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def narrate(
    state: Dict[str, Any],
    player_input: str,
    *,
    premium: bool = False,
    extra_context: Optional[str] = None,
) -> NarratorResponse:
    """Generate narration for a player action.

    This is the primary entry point.  It:

    1. Assembles the full message list (system prompt + history + input).
    2. Selects the model (standard or premium).
    3. Calls the LLM via :func:`canon_engine.openai_client.chat_completion`.
    4. Parses the response into a :class:`NarratorResponse`.

    Parameters
    ----------
    state : dict
        The current game state.
    player_input : str
        The player's action or dialogue (already parsed by the command
        parser; raw text expected here).
    premium : bool
        If ``True``, use the premium model (for major story beats).
    extra_context : str, optional
        Additional context injected as a user message before the player
        input (e.g. a system note about the current scene).

    Returns
    -------
    NarratorResponse
        Structured narration with optional state updates and layout hints.
    """
    model = resolve_model(premium=premium)
    logger.info("Narrate: model=%s premium=%s input=%r", model, premium, player_input[:80])

    messages = _build_history(state, player_input)

    if extra_context:
        # Insert before the final user message.
        messages.insert(-1, {"role": "user", "content": f"[System note: {extra_context}]"})

    raw_text = chat_completion(messages, model=model)
    logger.debug("Raw LLM output (%d chars): %s", len(raw_text), raw_text[:200])

    return parse_narration(raw_text, model=model)
