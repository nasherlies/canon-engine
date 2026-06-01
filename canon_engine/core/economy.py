"""Canon Engine — Economy system: wallet, merchants, buying/selling, scavenging."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from canon_engine.core.npc import shop_price_multiplier, get_npc, primary_merchant_npc_id

# ── Content loader ────────────────────────────────────────────────────────

_CONTENT_DIR = Path(os.environ.get(
    "CANON_CONTENT_DIR",
    Path(__file__).resolve().parents[2] / "content",
))


def _load_json(name: str) -> dict:
    p = _CONTENT_DIR / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, val))


# ── Wallet ────────────────────────────────────────────────────────────────

def ensure_wallet(state: dict[str, Any]) -> dict[str, Any]:
    """Ensure player has gold and gold_spent fields."""
    p = state.setdefault("player", {})
    p.setdefault("gold", 0)
    p.setdefault("gold_spent", 0)
    return p


# ── Victory rewards ───────────────────────────────────────────────────────

def grant_victory_gold_and_parts(state: dict[str, Any], enemies: list[dict], rng: Any) -> dict:
    """Grant gold drops and monster parts from defeated enemies."""
    player = ensure_wallet(state)
    total_gold = 0
    parts_dropped: list[dict] = []

    parts_data = _load_json("monster_parts.json")
    # parts_data is {enemy_type: [{name, rarity, base_value}, ...]}

    for enemy in enemies:
        etype = (enemy.get("type") or enemy.get("enemy_type") or "").lower()
        # Gold drop: 1-3 * enemy CR or level
        cr = enemy.get("cr", enemy.get("level", 1))
        gold_drop = rng.randint(1, max(1, cr * 3))
        total_gold += gold_drop

        # Parts drop
        if etype in parts_data:
            for part in parts_data[etype]:
                if rng.random() < 0.5:  # 50% chance per part
                    parts_dropped.append(part)

    player["gold"] = player.get("gold", 0) + total_gold
    # Add parts to inventory
    inv = state.setdefault("inventory", [])
    for part in parts_dropped:
        inv.append(part["name"])

    return {"gold": total_gold, "parts": parts_dropped}


# ── Pricing ───────────────────────────────────────────────────────────────

def calculate_buy_price(state: dict[str, Any], item: dict[str, Any], npc_id: str | None = None) -> int:
    """Calculate buy price: base price * shop multiplier."""
    base = item.get("price", 0)
    mult = 1.0
    if npc_id:
        mult = shop_price_multiplier(state, npc_id)
    return max(1, int(math.ceil(base * mult)))


def calculate_sell_price(state: dict[str, Any], item: dict[str, Any], npc_id: str | None = None) -> int:
    """Sell price = 50% of buy price, minimum 1."""
    buy = calculate_buy_price(state, item, npc_id)
    return max(1, buy // 2)


# ── Scavenging ────────────────────────────────────────────────────────────

def resolve_scavenge(state: dict[str, Any], rng: Any) -> dict:
    """LCK check vs location scavenge_dc (default 14)."""
    player = state.get("player", {})
    lck = player.get("stats", {}).get("LCK", 10)
    lck_mod = (lck - 10) // 2
    roll = rng.randint(1, 20)
    total = roll + lck_mod
    dc = state.get("world", {}).get("scavenge_dc", 14)

    if total >= dc:
        # Find something
        gold = rng.randint(1, 10)
        player.setdefault("gold", 0)
        player["gold"] += gold
        return {"success": True, "roll": roll, "total": total, "dc": dc, "gold_found": gold, "item_found": None}
    return {"success": False, "roll": roll, "total": total, "dc": dc, "gold_found": 0, "item_found": None}


# ── Bartering ─────────────────────────────────────────────────────────────

def resolve_barter(state: dict[str, Any], npc_id: str, rng: Any) -> dict:
    """CHA DC 12 check; on pass, 10% discount."""
    player = state.get("player", {})
    cha = player.get("stats", {}).get("CHA", 10)
    cha_mod = (cha - 10) // 2
    roll = rng.randint(1, 20)
    total = roll + cha_mod
    dc = 12

    if total >= dc:
        return {"success": True, "roll": roll, "total": total, "dc": dc, "discount": 0.10}
    return {"success": False, "roll": roll, "total": total, "dc": dc, "discount": 0.0}


# ── Renting ───────────────────────────────────────────────────────────────

def resolve_rent(state: dict[str, Any], inn_cost: int = 10) -> dict:
    """Pay gold for rest: +480 min, well_rested, sheltered."""
    player = ensure_wallet(state)
    if player["gold"] < inn_cost:
        return {"success": False, "reason": "Not enough gold", "gold": player["gold"], "cost": inn_cost}

    player["gold"] -= inn_cost
    player["gold_spent"] = player.get("gold_spent", 0) + inn_cost

    world = state.setdefault("world", {})
    world["minutes_total"] = world.get("minutes_total", 480) + 480
    world["sheltered"] = True

    # Apply well_rested status
    statuses = player.setdefault("statuses", [])
    if not any(s.get("id") == "well_rested" for s in statuses if isinstance(s, dict)):
        statuses.append({"id": "well_rested", "name": "Well Rested", "duration": 480, "effects": {"hp_regen": 2}})

    return {"success": True, "gold_spent": inn_cost, "minutes_gained": 480, "well_rested": True, "sheltered": True}


# ── Merchant stock ────────────────────────────────────────────────────────

def generate_merchant_stock(state: dict[str, Any], rng: Any) -> list[dict]:
    """Generate random merchant stock from catalogs."""
    catalogs = _load_json("merchants.json")
    catalog = catalogs.get("default", {})
    all_items = catalog.get("items", [])

    if not all_items:
        return []

    # Pick 4-8 items
    count = rng.randint(4, min(8, len(all_items)))
    return rng.sample(all_items, count)


def format_shop(state: dict[str, Any]) -> str:
    """Format merchant inventory display."""
    shop = state.get("world", {}).get("merchant_stock", [])
    merchant_id = primary_merchant_npc_id(state)
    mult = 1.0
    if merchant_id:
        mult = shop_price_multiplier(state, merchant_id)

    if not shop:
        return "No merchant here."

    lines = [f"**Shop** (price modifier: {mult:.1f}x)"]
    for i, item in enumerate(shop, 1):
        price = max(1, int(math.ceil(item.get("price", 0) * mult)))
        lines.append(f"  {i}. **{item['name']}** — {price}g ({item.get('rarity', 'common')})")
    return "\n".join(lines)


# ── Buy / Sell ────────────────────────────────────────────────────────────

def resolve_buy(state: dict[str, Any], item_name: str, npc_id: str | None, rng: Any) -> dict:
    """Buy an item from a merchant."""
    player = ensure_wallet(state)
    shop = state.get("world", {}).get("merchant_stock", [])

    # Find item in shop
    item = None
    for s in shop:
        if s["name"].lower() == item_name.lower():
            item = s
            break

    if item is None:
        return {"success": False, "reason": f"'{item_name}' not found in shop."}

    price = calculate_buy_price(state, item, npc_id)
    if player["gold"] < price:
        return {"success": False, "reason": f"Not enough gold. Need {price}, have {player['gold']}."}

    player["gold"] -= price
    player["gold_spent"] = player.get("gold_spent", 0) + price
    inv = state.setdefault("inventory", [])
    inv.append(item["name"])
    shop.remove(item)

    return {"success": True, "item": item["name"], "price": price, "gold_remaining": player["gold"]}


def resolve_sell(state: dict[str, Any], item_name: str, npc_id: str | None = None) -> dict:
    """Sell an item from inventory."""
    player = ensure_wallet(state)
    inv = state.get("inventory", [])

    # Find item in inventory
    found = None
    for i_name in inv:
        if i_name.lower() == item_name.lower():
            found = i_name
            break

    if found is None:
        return {"success": False, "reason": f"'{item_name}' not in inventory."}

    # Estimate item value (default 10)
    item = {"name": found, "price": 10}
    price = calculate_sell_price(state, item, npc_id)

    inv.remove(found)
    player["gold"] = player.get("gold", 0) + price

    return {"success": True, "item": found, "price": price, "gold_total": player["gold"]}
