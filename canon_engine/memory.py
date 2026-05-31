"""Three-tier memory stack for Canon Engine.

Provides the narrator with contextually relevant memory so it can maintain
narrative continuity across sessions.

Memory tiers
------------
**Hot** – The last *N* raw world-log entries (verbatim).  Cheap, always
available, gives the LLM the immediate narrative context.

**Warm** – AI-generated summaries stored in the game state's ``memory``
list.  Each entry is a short paragraph that captures the essence of a
block of play.

**Cold** – ChromaDB vector search for semantic recall.  *Stubbed for now*;
always returns an empty list.

Public API
----------
* ``get_memory_context(state, topic=None) -> str``
* ``build_hot_memory(world_log, limit=20) -> list[str]``
* ``build_warm_memory(memory_entries) -> list[str]``
* ``build_cold_memory(query, state, limit=5) -> list[str]``
* ``format_memory_for_prompt(hot, warm, cold) -> str``
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from canon_engine.constants import WORLD_LOG_LIMIT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Number of recent world-log entries kept in hot memory.
HOT_MEMORY_TURNS: int = 20

#: Maximum warm-memory entries injected into a single prompt.
WARM_MEMORY_LIMIT: int = 10

#: Maximum cold-memory results to inject.
COLD_MEMORY_LIMIT: int = 5


# ---------------------------------------------------------------------------
# Hot memory
# ---------------------------------------------------------------------------


def build_hot_memory(
    world_log: Sequence[Any],
    *,
    limit: int = HOT_MEMORY_TURNS,
) -> List[str]:
    """Return the most recent *limit* entries from the world log.

    Parameters
    ----------
    world_log : sequence
        The ``state["world_log"]`` list.  Each element may be a ``str`` or a
        dict with a ``"text"`` or ``"content"`` key.
    limit : int
        How many recent entries to keep.

    Returns
    -------
    list of str
        The most recent entries as plain strings, oldest-first.
    """
    if not world_log:
        return []

    # Slice the tail.
    recent = list(world_log[-limit:])
    result: List[str] = []
    for entry in recent:
        if isinstance(entry, str):
            result.append(entry)
        elif isinstance(entry, dict):
            result.append(
                entry.get("text")
                or entry.get("content")
                or str(entry)
            )
        else:
            result.append(str(entry))
    return result


# ---------------------------------------------------------------------------
# Warm memory
# ---------------------------------------------------------------------------


def build_warm_memory(
    memory_entries: Sequence[Any],
    *,
    limit: int = WARM_MEMORY_LIMIT,
) -> List[str]:
    """Return up to *limit* warm-memory summaries.

    Warm-memory entries are stored in ``state["memory"]`` as dicts with at
    least a ``"summary"`` key.  Plain strings are also accepted.

    Parameters
    ----------
    memory_entries : sequence
        The ``state["memory"]`` list.
    limit : int
        Maximum entries to return.

    Returns
    -------
    list of str
        Summaries, newest-first.
    """
    if not memory_entries:
        return []

    # Take the most recent entries.
    recent = list(memory_entries[-limit:])
    result: List[str] = []
    for entry in reversed(recent):  # newest first
        if isinstance(entry, str):
            result.append(entry)
        elif isinstance(entry, dict):
            result.append(
                entry.get("summary")
                or entry.get("text")
                or entry.get("content")
                or str(entry)
            )
        else:
            result.append(str(entry))
    return result


# ---------------------------------------------------------------------------
# Cold memory (ChromaDB stub)
# ---------------------------------------------------------------------------


def build_cold_memory(
    query: str,
    state: Dict[str, Any],
    *,
    limit: int = COLD_MEMORY_LIMIT,
) -> List[str]:
    """Semantic vector search over historical narration (ChromaDB stub).

    This function will eventually perform a similarity search against a
    ChromaDB collection seeded from past world-log entries.  For now it
    always returns an empty list.

    Parameters
    ----------
    query : str
        A natural-language query to search for.
    state : dict
        The full game state (needed for future collection routing).
    limit : int
        Maximum results to return.

    Returns
    -------
    list of str
        Matching narration excerpts (currently always empty).
    """
    # TODO: Implement ChromaDB vector search.
    # 1. Initialise or retrieve a ChromaDB collection for this state/project.
    # 2. Perform a similarity search with *query*.
    # 3. Return the top *limit* results as plain strings.
    _ = (query, state, limit)  # suppress unused-argument warnings
    logger.debug("Cold memory (ChromaDB) is stubbed — returning empty list.")
    return []


# ---------------------------------------------------------------------------
# Aggregated context builder
# ---------------------------------------------------------------------------


def format_memory_for_prompt(
    hot: Sequence[str],
    warm: Sequence[str],
    cold: Sequence[str],
) -> str:
    """Format all three memory tiers into a single prompt-injectable block.

    Returns
    -------
    str
        A Markdown-formatted section ready to embed in a system or user
        message.  Returns ``""`` if all tiers are empty.
    """
    sections: List[str] = []

    if warm:
        sections.append("## Prior Summary (Warm Memory)")
        for i, s in enumerate(warm, 1):
            sections.append(f"{i}. {s}")

    if hot:
        sections.append("")
        sections.append("## Recent Events (Hot Memory — last turns)")
        for entry in hot:
            sections.append(f"- {entry}")

    if cold:
        sections.append("")
        sections.append("## Recalled Fragments (Cold Memory — semantic)")
        for i, fragment in enumerate(cold, 1):
            sections.append(f"{i}. {fragment}")

    if not sections:
        return ""

    return "\n".join(sections)


def get_memory_context(
    state: Dict[str, Any],
    *,
    topic: Optional[str] = None,
) -> str:
    """Build the full memory context string for narrator injection.

    This is the primary entry point used by the narrator.  It queries all
    three memory tiers and returns a single formatted string.

    Parameters
    ----------
    state : dict
        The current game state.
    topic : str, optional
        A topic hint for cold-memory search (e.g. the player's last action).

    Returns
    -------
    str
        Formatted memory block.  May be ``""`` if the state is fresh.
    """
    hot = build_hot_memory(state.get("world_log", []))
    warm = build_warm_memory(state.get("memory", []))

    query = topic or (hot[-1] if hot else "")
    cold = build_cold_memory(query, state) if query else []

    return format_memory_for_prompt(hot, warm, cold)
