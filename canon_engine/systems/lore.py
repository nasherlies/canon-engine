"""Lore query, world bible management."""

from __future__ import annotations

from typing import Any


def get_lore_book(state: dict[str, Any]) -> dict[str, str]:
    return state.setdefault("lore_book", {})


def add_lore_entry(state: dict[str, Any], key: str, text: str) -> None:
    get_lore_book(state)[key.lower()] = text


def query_lore(state: dict[str, Any], query: str) -> dict[str, Any]:
    book = get_lore_book(state)
    key = query.lower().strip()
    if key in book:
        return {"narration": book[key], "found": True}
    # Partial match
    matches = [v for k, v in book.items() if key in k]
    if matches:
        return {"narration": matches[0], "found": True}
    return {"narration": f"No lore found for '{query}'.", "found": False}
