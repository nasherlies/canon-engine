"""
Canon Engine — Equipment Suggest

Provides upgrade hint lines when a player equips an item,
checking for higher-rarity alternatives in the same slot.
"""

from __future__ import annotations

from typing import Any

from canon_engine.core.rarity import RARITY_MAP


def upgrade_hint_line(state: dict[str, Any], just_equipped_slot: str) -> str | None:
    """
    After equipping to `just_equipped_slot`, check inventory for a
    higher-rarity piece that fits the same slot.

    Returns a hint string, or None if no upgrade found.
    """
    eq = state.get("equipment", {})
    current = eq.get(just_equipped_slot)
    if not current:
        return None

    current_rarity = RARITY_MAP.get(current.get("rarity", "common").lower(), 0)
    best_alt: dict[str, Any] | None = None
    best_rarity = current_rarity

    for it in state.get("inventory", []):
        # Check if item fits this slot
        item_slot = it.get("equip_slot", "").lower()
        if item_slot == just_equipped_slot or _slot_matches(item_slot, just_equipped_slot):
            it_rarity = RARITY_MAP.get(it.get("rarity", "common").lower(), 0)
            if it_rarity > best_rarity:
                best_rarity = it_rarity
                best_alt = it

    if best_alt:
        return (
            f"💡 You have **{best_alt['name']}** "
            f"({best_alt.get('rarity', 'common').title()}) in your bag — "
            f"it's better than what you just equipped."
        )
    return None


def _slot_matches(item_slot: str, target_slot: str) -> bool:
    """Check if an item's slot alias resolves to the target slot."""
    from canon_engine.core.inventory import _SLOT_ALIASES, EQUIP_SLOTS

    if item_slot == target_slot:
        return True
    if item_slot not in EQUIP_SLOTS:
        mapped = _SLOT_ALIASES.get(item_slot)
        if mapped == target_slot:
            return True
        # Ring/accessory dual-slot
        if item_slot == "ring" and target_slot in ("ring_left", "ring_right"):
            return True
        if item_slot in ("accessory", "curio") and target_slot in ("accessory_1", "accessory_2"):
            return True
    return False
