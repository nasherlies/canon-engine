"""
Canon Engine — Inventory System

17-slot Curios-style equipment with item normalization, equip/unequip,
carry-weight tracking, and inventory sheet formatting.
"""

from __future__ import annotations

import copy
import hashlib
import re
from typing import Any

from canon_engine.core.rarity import RARITY_MAP, is_notable
from canon_engine.core.stats import STAT_KEYS, get_stat_modifier

# ───────────────────────────────────────────────────────────────────
# Equipment slot taxonomy (17 slots)
# ───────────────────────────────────────────────────────────────────
EQUIP_SLOTS: dict[str, str] = {
    "head":            "HEAD",
    "face":            "FACE",
    "neck":            "NECK",
    "back":            "BACK",
    "chest_armor":     "CHEST · ARMOR",
    "chest_clothing":  "CHEST · CLOTH",
    "hands":           "HANDS",
    "waist":           "WAIST",
    "legs_armor":      "LEGS · ARMOR",
    "legs_clothing":   "LEGS · CLOTH",
    "feet":            "FEET",
    "ring_left":       "RING · L",
    "ring_right":      "RING · R",
    "weapon_main":     "WEAPON · MAIN",
    "weapon_off":      "WEAPON · OFF",
    "accessory_1":     "ACC · 1",
    "accessory_2":     "ACC · 2",
}

# Weight of a single gold coin
GOLD_WEIGHT_PER_COIN: float = 0.02

# ───────────────────────────────────────────────────────────────────
# Slot alias mapping
# ───────────────────────────────────────────────────────────────────
_SLOT_ALIASES: dict[str, str] = {
    "weapon":     "weapon_main",
    "armor":      "chest_armor",
    "shield":     "weapon_off",
    "shirt":      "chest_clothing",
    "boots":      "feet",
    "gloves":     "hands",
    "pants":      "legs_clothing",
    "greaves":    "legs_armor",
    "amulet":     "neck",
    "cloak":      "back",
    "belt":       "waist",
    "helm":       "head",
    "helmet":     "head",
    "hat":        "head",
    "mask":       "face",
    "goggles":    "face",
    "bracers":    "hands",
    "gauntlets":  "hands",
    "leggings":   "legs_clothing",
    "trousers":   "legs_clothing",
    "shoulders":  "back",
    "cape":       "back",
    "pendant":    "neck",
    "torso":      "chest_armor",
    "chest":      "chest_armor",
    "ring":       "ring_left",       # resolved dynamically below
    "accessory":  "accessory_1",     # resolved dynamically below
    "curio":      "accessory_1",     # resolved dynamically below
}

# ───────────────────────────────────────────────────────────────────
# Legacy slot migration map (4-slot → 17-slot)
# ───────────────────────────────────────────────────────────────────
_LEGACY_SLOT_MAP: dict[str, str] = {
    "weapon":      "weapon_main",
    "torso":       "chest_armor",
    "accessory_1": "accessory_1",
    "accessory_2": "accessory_2",
}


# ═══════════════════════════════════════════════════════════════════
# Item normalization
# ═══════════════════════════════════════════════════════════════════

def _slugify(name: str) -> str:
    """Convert a name to a lowercase slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "item"


def _short_hash(name: str) -> str:
    """Return a 6-char hex hash derived from a name."""
    return hashlib.sha256(name.encode()).hexdigest()[:6]


def normalize_item(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Ensure an item dict has all canonical fields.

    Fields: id, name, rarity, qty, weight, itype, effects, tags,
            equip_slot, consumable, lore.
    """
    item = dict(raw)  # shallow copy

    name = item.get("name", "Unknown Item")
    item["name"] = name

    # Generate id from name slug + short hash if missing
    if not item.get("id"):
        item["id"] = f"{_slugify(name)}-{_short_hash(name)}"

    item.setdefault("rarity", "common")
    item.setdefault("qty", 1)
    item.setdefault("weight", 0.0)
    item.setdefault("itype", "misc")
    item.setdefault("effects", {})
    item.setdefault("tags", [])
    item.setdefault("equip_slot", "")
    item.setdefault("consumable", False)
    item.setdefault("lore", "")

    return item


def ensure_inventory_items(state: dict[str, Any]) -> None:
    """Normalize every item in state['inventory'] in-place."""
    inv = state.setdefault("inventory", [])
    state["inventory"] = [normalize_item(it) for it in inv]


def ensure_equipment(state: dict[str, Any]) -> None:
    """
    Migrate legacy 4-slot equipment to 17-slot layout.

    Old keys: weapon, torso, accessory_1, accessory_2
    """
    eq = state.setdefault("equipment", {})
    for old_key, new_key in _LEGACY_SLOT_MAP.items():
        if old_key in eq and new_key not in eq:
            eq[new_key] = eq.pop(old_key)
        elif old_key in eq and new_key in eq:
            # new_key already present — drop legacy
            eq.pop(old_key, None)

    # Ensure every 17-slot key exists (None = empty)
    for slot_key in EQUIP_SLOTS:
        eq.setdefault(slot_key, None)


# ═══════════════════════════════════════════════════════════════════
# Slot resolution
# ═══════════════════════════════════════════════════════════════════

def resolve_equip_slot(token: str, eq: dict[str, Any]) -> str:
    """
    Map a user-facing slot alias to a canonical 17-slot key.

    For ring / accessory / curio: picks the first empty slot,
    or ring_left / accessory_1 if both occupied.
    """
    t = token.strip().lower()

    # Direct match
    if t in EQUIP_SLOTS:
        return t

    # Alias match
    mapped = _SLOT_ALIASES.get(t)
    if mapped:
        # For ring and accessory aliases, pick the first free slot
        if t == "ring":
            return "ring_left" if eq.get("ring_left") is None else "ring_right"
        if t in ("accessory", "curio"):
            return "accessory_1" if eq.get("accessory_1") is None else "accessory_2"
        return mapped

    # Fallback: return as-is (caller validates)
    return t


# ═══════════════════════════════════════════════════════════════════
# Core operations
# ═══════════════════════════════════════════════════════════════════

def _find_item(state: dict[str, Any], name: str) -> tuple[int, dict[str, Any]] | tuple[None, None]:
    """Find an item in inventory by name (case-insensitive). Lower index = first match."""
    target = name.strip().lower()
    for i, it in enumerate(state.get("inventory", [])):
        if it.get("name", "").lower() == target:
            return i, it
    # Fuzzy: substring
    for i, it in enumerate(state.get("inventory", [])):
        if target in it.get("name", "").lower():
            return i, it
    return None, None


def _find_slot_for_item(item: dict[str, Any], eq: dict[str, Any]) -> str | None:
    """Determine the best equip slot for an item based on its equip_slot field."""
    preferred = item.get("equip_slot", "").strip().lower()
    if preferred:
        if preferred in EQUIP_SLOTS:
            return preferred
        mapped = _SLOT_ALIASES.get(preferred)
        if mapped:
            return resolve_equip_slot(preferred, eq)
    return None


def equip_item(state: dict[str, Any], item_name: str) -> dict[str, Any]:
    """
    Equip an item from inventory to its appropriate slot.

    Returns a result dict with 'ok', 'message', and optionally 'slot', 'unequipped'.
    """
    idx, item = _find_item(state, item_name)
    if item is None:
        return {"ok": False, "message": f"You don't have '{item_name}'."}

    eq = state.setdefault("equipment", {})
    ensure_equipment(state)

    slot = _find_slot_for_item(item, eq)
    if not slot:
        return {"ok": False, "message": f"'{item['name']}' is not equippable."}

    if slot not in EQUIP_SLOTS:
        return {"ok": False, "message": f"Unknown slot '{slot}'."}

    # Remove from inventory
    state["inventory"].pop(idx)

    # Unequip what's currently there
    unequipped = None
    current = eq.get(slot)
    if current:
        unequipped = current
        state["inventory"].append(current)

    # Equip new item
    eq[slot] = item

    msg = f"Equipped **{item['name']}** → {EQUIP_SLOTS[slot]}."
    result: dict[str, Any] = {"ok": True, "message": msg, "slot": slot, "item": item}
    if unequipped:
        result["unequipped"] = unequipped
        result["message"] += f" Swapped out **{unequipped['name']}**."
    return result


def unequip_item(state: dict[str, Any], slot: str) -> dict[str, Any]:
    """Unequip an item from a slot back to inventory."""
    ensure_equipment(state)
    eq = state.get("equipment", {})

    # Resolve alias
    real_slot = resolve_equip_slot(slot, eq)
    if real_slot not in EQUIP_SLOTS:
        return {"ok": False, "message": f"Unknown slot '{slot}'."}

    current = eq.get(real_slot)
    if not current:
        return {"ok": False, "message": f"Nothing equipped in {EQUIP_SLOTS[real_slot]}."}

    eq[real_slot] = None
    state.setdefault("inventory", []).append(current)
    sync_carry(state)
    return {
        "ok": True,
        "message": f"Unequipped **{current['name']}** from {EQUIP_SLOTS[real_slot]}.",
        "item": current,
    }


def use_item(state: dict[str, Any], item_name: str, rng: Any = None) -> dict[str, Any]:
    """
    Use an item: equip/unequip toggle or consume a consumable.
    """
    import random
    rng = rng or random.Random()

    idx, item = _find_item(state, item_name)
    if item is None:
        return {"ok": False, "message": f"You don't have '{item_name}'."}

    # Consumable path
    if item.get("consumable"):
        apply_consumable_effects(state, item)
        # Deduct qty
        item["qty"] = item.get("qty", 1) - 1
        if item["qty"] <= 0:
            state["inventory"].pop(idx)
        sync_carry(state)
        return {"ok": True, "message": f"Used **{item['name']}**.", "consumed": True}

    # Equip/unequip toggle
    if item.get("equip_slot"):
        # Check if already equipped
        eq = state.get("equipment", {})
        for s, equipped in eq.items():
            if equipped and equipped.get("id") == item.get("id"):
                return unequip_item(state, s)
        return equip_item(state, item_name)

    return {"ok": False, "message": f"'{item['name']}' can't be used."}


def drop_item(
    state: dict[str, Any], item_name: str, confirm: bool = False
) -> dict[str, Any]:
    """
    Drop an item from inventory.  Rare+ requires confirm=True.
    """
    idx, item = _find_item(state, item_name)
    if item is None:
        return {"ok": False, "message": f"You don't have '{item_name}'."}

    rarity = item.get("rarity", "common").lower()
    tier = RARITY_MAP.get(rarity, {}).get("rank", 0) if isinstance(RARITY_MAP.get(rarity), dict) else 0
    if tier >= 2 and not confirm:
        return {
            "ok": False,
            "message": f"**{item['name']}** is {rarity.title()}. Re-run with --confirm to drop.",
            "needs_confirm": True,
        }

    state["inventory"].pop(idx)
    sync_carry(state)
    return {"ok": True, "message": f"Dropped **{item['name']}**.", "item": item}


def combine_items(
    state: dict[str, Any],
    item1_name: str,
    item2_name: str,
    rng: Any = None,
) -> dict[str, Any]:
    """
    Attempt to combine two items.  Stub: always fails gracefully.
    """
    import random
    rng = rng or random.Random()

    idx1, it1 = _find_item(state, item1_name)
    idx2, it2 = _find_item(state, item2_name)

    if it1 is None:
        return {"ok": False, "message": f"You don't have '{item1_name}'."}
    if it2 is None:
        return {"ok": False, "message": f"You don't have '{item2_name}'."}
    if it1.get("id") == it2.get("id"):
        return {"ok": False, "message": "Can't combine an item with itself."}

    # No built-in recipes — return failure
    return {
        "ok": False,
        "message": f"**{it1['name']}** and **{it2['name']}** don't combine into anything.",
    }


def give_item(
    state: dict[str, Any], item_name: str, recipient: str
) -> dict[str, Any]:
    """Transfer an item from inventory to a named recipient."""
    idx, item = _find_item(state, item_name)
    if item is None:
        return {"ok": False, "message": f"You don't have '{item_name}'."}

    state["inventory"].pop(idx)
    sync_carry(state)
    return {
        "ok": True,
        "message": f"Gave **{item['name']}** to **{recipient}**.",
        "item": item,
        "recipient": recipient,
    }


# ═══════════════════════════════════════════════════════════════════
# Consumable helpers
# ═══════════════════════════════════════════════════════════════════

def apply_consumable_effects(state: dict[str, Any], item: dict[str, Any]) -> None:
    """
    Apply heal_hp, remove_status, apply_status from a consumable item's effects.
    """
    effects = item.get("effects", {})

    # heal_hp
    heal = effects.get("heal_hp", 0)
    if heal:
        state["hp"] = min(state.get("hp", 0) + heal, state.get("max_hp", heal))

    # remove_status
    remove = effects.get("remove_status", [])
    if isinstance(remove, str):
        remove = [remove]
    for status_name in remove:
        statuses = state.get("statuses", [])
        state["statuses"] = [s for s in statuses if s.get("name", "").lower() != status_name.lower()]

    # apply_status
    apply = effects.get("apply_status", [])
    if isinstance(apply, str):
        apply = [apply]
    elif isinstance(apply, dict):
        apply = [apply]
    for status_entry in apply:
        if isinstance(status_entry, str):
            state.setdefault("statuses", []).append({"name": status_entry, "duration": 3})
        elif isinstance(status_entry, dict):
            state.setdefault("statuses", []).append(status_entry)


def deduct_consumable_matched(state: dict[str, Any], item_name: str) -> bool:
    """
    Deduct one charge from a consumable matching item_name.
    Returns True if the item was found and deducted.
    """
    idx, item = _find_item(state, item_name)
    if item is None or not item.get("consumable"):
        return False

    item["qty"] = item.get("qty", 1) - 1
    if item["qty"] <= 0:
        state["inventory"].pop(idx)
    return True


# ═══════════════════════════════════════════════════════════════════
# Carry weight
# ═══════════════════════════════════════════════════════════════════

def sync_carry(state: dict[str, Any]) -> None:
    """
    Recalculate carry weight from inventory + equipped + gold.
    Apply Fatigued status if over capacity (30 + STR×2).
    """
    total = 0.0

    # Inventory
    for it in state.get("inventory", []):
        total += it.get("weight", 0.0) * it.get("qty", 1)

    # Equipped
    for slot, equipped in state.get("equipment", {}).items():
        if equipped:
            total += equipped.get("weight", 0.0)

    # Gold weight
    gold = state.get("gold", 0)
    total += gold * GOLD_WEIGHT_PER_COIN

    state["carry_weight"] = round(total, 2)

    # Capacity check
    stats = state.get("stats", {})
    strength = stats.get("STR", 10)
    capacity = 30 + strength * 2

    state["carry_capacity"] = capacity

    if total > capacity:
        # Add Fatigued status
        statuses = state.setdefault("statuses", [])
        if not any(s.get("name") == "Fatigued" for s in statuses):
            statuses.append({"name": "Fatigued", "duration": -1, "source": "encumbrance"})
    else:
        # Remove Fatigued from encumbrance
        statuses = state.get("statuses", [])
        state["statuses"] = [s for s in statuses if not (s.get("name") == "Fatigued" and s.get("source") == "encumbrance")]


# ═══════════════════════════════════════════════════════════════════
# Display / formatting
# ═══════════════════════════════════════════════════════════════════

def _rarity_icon(rarity: str) -> str:
    """Return a display icon for a rarity tier."""
    icons = {
        "common": "⬜",
        "uncommon": "🟩",
        "rare": "🟦",
        "epic": "🟪",
        "legendary": "🟧",
        "mythic": "🟥",
    }
    return icons.get(rarity.lower(), "⬜")


def format_inventory_sheet(state: dict[str, Any]) -> str:
    """
    Render a full inventory sheet as formatted text.
    """
    lines: list[str] = []

    # Equipped items
    eq = state.get("equipment", {})
    lines.append("── EQUIPPED ──")
    for slot_key, display_name in EQUIP_SLOTS.items():
        equipped = eq.get(slot_key)
        if equipped:
            icon = _rarity_icon(equipped.get("rarity", "common"))
            lines.append(f"  {display_name:16s}  {icon} {equipped['name']}")
        else:
            lines.append(f"  {display_name:16s}  —")

    # Bag items
    inv = state.get("inventory", [])
    lines.append("")
    lines.append(f"── BAG ({len(inv)} items) ──")
    if not inv:
        lines.append("  (empty)")
    else:
        for it in inv:
            icon = _rarity_icon(it.get("rarity", "common"))
            qty_str = f" ×{it['qty']}" if it.get("qty", 1) > 1 else ""
            lines.append(f"  {icon} {it['name']}{qty_str}")

    # Carry
    cw = state.get("carry_weight", 0)
    cc = state.get("carry_capacity", 30)
    lines.append(f"\n📦 Carry: {cw:.1f} / {cc}")

    # Gold
    gold = state.get("gold", 0)
    if gold:
        lines.append(f"💰 Gold: {gold}")

    return "\n".join(lines)


def format_inventory_rows(state: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Return inventory + equipment as a flat list of row dicts (JSON API).
    """
    rows: list[dict[str, Any]] = []

    eq = state.get("equipment", {})
    for slot_key, display_name in EQUIP_SLOTS.items():
        equipped = eq.get(slot_key)
        if equipped:
            rows.append({
                "location": "equipped",
                "slot": slot_key,
                "slot_label": display_name,
                "name": equipped["name"],
                "rarity": equipped.get("rarity", "common"),
                "qty": 1,
            })

    for it in state.get("inventory", []):
        rows.append({
            "location": "bag",
            "slot": "",
            "slot_label": "",
            "name": it["name"],
            "rarity": it.get("rarity", "common"),
            "qty": it.get("qty", 1),
        })

    return rows
