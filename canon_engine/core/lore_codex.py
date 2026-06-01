"""
Canon Engine — Lore Codex

Discoverable lore cards that accumulate as the player explores.
Cards are organized by category: character, location, faction, item, history.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

# ── Content loader ────────────────────────────────────────────────────

_CONTENT_DIR = Path(os.environ.get(
    "CANON_CONTENT_DIR",
    Path(__file__).resolve().parents[2] / "content",
))


def _load_json(name: str) -> dict:
    p = _CONTENT_DIR / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


# ── ID generation ─────────────────────────────────────────────────────

def slug_for(title: str, category: str) -> str:
    """Generate a stable id from title + category."""
    base = re.sub(r"[^a-z0-9]+", "_", (title + "_" + category).lower()).strip("_")
    return base


# ── Card normalization ────────────────────────────────────────────────

_VALID_CATEGORIES = {"character", "location", "faction", "item", "history"}


def normalize_card(raw: dict, turn: int = 0) -> dict:
    """Validate and normalize a lore card dict."""
    title = raw.get("title", "Unknown")
    category = raw.get("category", "history")
    if category not in _VALID_CATEGORIES:
        category = "history"

    card_id = raw.get("id") or slug_for(title, category)

    return {
        "id": card_id,
        "title": title,
        "category": category,
        "description": raw.get("description", ""),
        "source": raw.get("source", "unknown"),
        "discovered_at_turn": raw.get("discovered_at_turn", turn),
        "locked": raw.get("locked", False),
    }


# ── Codex management ─────────────────────────────────────────────────

def ensure_codex(state: dict[str, Any]) -> None:
    """Ensure state['lore_cards'] exists."""
    state.setdefault("lore_cards", [])


def seed_initial_codex(state: dict[str, Any]) -> None:
    """Seed lore cards from seed_lore.json based on genre."""
    ensure_codex(state)
    lore_data = _load_json("lore/seed_lore.json")
    genres = lore_data.get("genres", {})

    genre = state.get("genre", state.get("world", {}).get("genre", "_default"))
    cards_raw = genres.get(genre, genres.get("_default", []))

    existing_ids = {c.get("id") for c in state.get("lore_cards", [])}

    for raw in cards_raw:
        card = normalize_card(raw, turn=0)
        if card["id"] not in existing_ids:
            state["lore_cards"].append(card)
            existing_ids.add(card["id"])


def discover_card(
    state: dict[str, Any],
    raw: dict,
    turn: int = 0,
    source: str = "narrator",
) -> dict:
    """Append a lore card if new. Returns the card (existing or new)."""
    ensure_codex(state)
    card = normalize_card(raw, turn=turn)
    card["source"] = source

    existing_ids = {c.get("id") for c in state.get("lore_cards", [])}
    if card["id"] in existing_ids:
        # Return existing card
        for c in state["lore_cards"]:
            if c["id"] == card["id"]:
                return c

    state["lore_cards"].append(card)
    return card


# ── Narrator integration ─────────────────────────────────────────────

def apply_discovered_lore_payload(
    state: dict[str, Any],
    updates: list[dict] | dict,
    turn: int = 0,
) -> list[str]:
    """Handle discovered_lore updates from narrator.

    Each update: {title, category, description, locked?}
    Returns log lines.
    """
    ensure_codex(state)

    if isinstance(updates, dict):
        updates = [updates]

    log_lines: list[str] = []
    pulse = state.setdefault("lore_pulse", [])

    for raw in updates:
        card = discover_card(state, raw, turn=turn, source="narrator")
        # Check if this was actually new (pulse only for new discoveries)
        is_new = any(
            c.get("id") == card["id"] and c.get("discovered_at_turn") == turn
            for c in state.get("lore_cards", [])
        )
        if is_new:
            log_lines.append(f"[LORE] Discovered: {card['title']} ({card['category']})")
            pulse.append({
                "type": "lore_discovered",
                "card_id": card["id"],
                "title": card["title"],
                "category": card["category"],
                "turn": turn,
            })

    return log_lines


# ── Pulse (per-turn events) ──────────────────────────────────────────

def drain_pulse(state: dict[str, Any]) -> list[dict]:
    """Read and clear per-turn lore events."""
    pulse = state.get("lore_pulse", [])
    state["lore_pulse"] = []
    return pulse


# ── API payload ───────────────────────────────────────────────────────

def codex_payload(state: dict[str, Any]) -> dict:
    """Return codex data for API consumption."""
    ensure_codex(state)
    cards = state.get("lore_cards", [])
    return {
        "total": len(cards),
        "unlocked": sum(1 for c in cards if not c.get("locked", False)),
        "locked": sum(1 for c in cards if c.get("locked", False)),
        "cards": cards,
    }
