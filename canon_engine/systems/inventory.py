"""Item management, rarity tiers, weight, equip/unequip."""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Rarity tiers
# ---------------------------------------------------------------------------

RARITY_TIERS = ["Dirt", "Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical"]
RARITY_WEIGHT_MULT = {r: i for i, r in enumerate(RARITY_TIERS)}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_inventory(state: dict[str, Any]) -> list[dict[str, Any]]:
    return state.setdefault("inventory", [])


def find_item(state: dict[str, Any], name: str) -> dict[str, Any] | None:
    """Case-insensitive search by item name."""
    lower = name.lower()
    for item in get_inventory(state):
        if item.get("name", "").lower() == lower:
            return item
    return None


def add_item(state: dict[str, Any], item: dict[str, Any]) -> bool:
    """Add item to inventory. Returns True on success."""
    get_inventory(state).append(item)
    return True


def remove_item(state: dict[str, Any], name: str) -> dict[str, Any] | None:
    """Remove and return item by name, or None."""
    inv = get_inventory(state)
    for i, item in enumerate(inv):
        if item.get("name", "").lower() == name.lower():
            return inv.pop(i)
    return None


def total_weight(state: dict[str, Any]) -> float:
    return sum(i.get("weight", 0) for i in get_inventory(state))


def is_encumbered(state: dict[str, Any]) -> bool:
    char = state.get("character", state)
    carry_cap = char.get("stats", {}).get("STR", 10) * 15
    return total_weight(state) > carry_cap


# ---------------------------------------------------------------------------
# Equip / unequip
# ---------------------------------------------------------------------------

def equip_item(state: dict[str, Any], item_name: str) -> dict[str, Any]:
    item = find_item(state, item_name)
    if item is None:
        return {"narration": f"You don't have '{item_name}'."}
    slot = item.get("slot", "main_hand")
    equipped = state.setdefault("equipped", {})
    # Swap out current
    old = equipped.get(slot)
    if old:
        add_item(state, old)
    equipped[slot] = remove_item(state, item_name)
    return {"narration": f"You equip the {item['name']}."}


def unequip_item(state: dict[str, Any], slot: str) -> dict[str, Any]:
    equipped = state.setdefault("equipped", {})
    item = equipped.pop(slot, None)
    if item is None:
        return {"narration": f"Nothing equipped in {slot}."}
    add_item(state, item)
    return {"narration": f"You unequip the {item['name']}."}


def get_inventory_summary(state: dict[str, Any]) -> str:
    inv = get_inventory(state)
    if not inv:
        return "Your inventory is empty."
    lines = [f"- {i['name']} ({i.get('rarity', 'Common')}) x{i.get('qty', 1)}" for i in inv]
    return "Inventory:\n" + "\n".join(lines)
