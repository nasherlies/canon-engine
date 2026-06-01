"""
Canon Engine — Starting Kits

Loads class-based starting kits from content/presets/starting_kits.json
and applies them to a fresh character state.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from canon_engine.core.inventory import normalize_item, ensure_equipment

# ───────────────────────────────────────────────────────────────────
# Locate content directory
# ───────────────────────────────────────────────────────────────────
_CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "content"
_KITS_PATH = _CONTENT_DIR / "presets" / "starting_kits.json"


def _load_kits() -> dict[str, Any]:
    """Load starting kits from JSON file."""
    if not _KITS_PATH.exists():
        return {}
    with open(_KITS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_starting_kit(state: dict[str, Any], preset_id: str) -> None:
    """
    Apply a starting kit to the character state in-place.

    preset_id matches a key in starting_kits.json (e.g. 'knight', 'rogue').
    """
    kits = _load_kits()
    kit = kits.get(preset_id.lower())
    if not kit:
        return

    inv = state.setdefault("inventory", [])
    eq = state.setdefault("equipment", {})
    ensure_equipment(state)

    # Add inventory items
    for raw_item in kit.get("inventory", []):
        item = normalize_item(raw_item)
        inv.append(item)

    # Equip items by slot
    equip_map = kit.get("equip", {})
    for slot, item_name in equip_map.items():
        # Find in inventory
        for i, it in enumerate(inv):
            if it.get("name", "").lower() == item_name.lower():
                eq[slot] = it
                inv.pop(i)
                break
