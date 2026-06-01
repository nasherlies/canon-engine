"""
Canon Engine — Item Lore

Loads and queries item lore entries from content/item_lore.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "content"
_LORE_PATH = _CONTENT_DIR / "item_lore.json"


def _load_lore_db() -> dict[str, str]:
    """Load the item lore database. Returns empty dict if file missing."""
    if not _LORE_PATH.exists():
        return {}
    with open(_LORE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data
    return {}


def get_item_lore(item_name: str) -> str | None:
    """
    Look up lore text for an item by name (case-insensitive).

    Returns the lore string, or None if no entry exists.
    """
    db = _load_lore_db()
    target = item_name.strip().lower()

    # Direct match
    if target in db:
        return db[target]

    # Case-insensitive scan
    for key, value in db.items():
        if key.lower() == target:
            return value

    return None
