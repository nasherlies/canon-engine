"""Shops, buy/sell/barter, currency, scavenge."""

from __future__ import annotations

import random
from typing import Any


def get_currency(state: dict[str, Any]) -> int:
    return state.get("currency", 0)


def add_currency(state: dict[str, Any], amount: int) -> int:
    state["currency"] = get_currency(state) + amount
    return state["currency"]


def buy_item(state: dict[str, Any], item_name: str, vendor: str = "") -> dict[str, Any]:
    """Buy item from a vendor. Stub implementation."""
    return {"narration": f"You attempt to buy {item_name} from {vendor or 'a vendor'}."}


def sell_item(state: dict[str, Any], item_name: str, vendor: str = "") -> dict[str, Any]:
    """Sell item to a vendor. Stub implementation."""
    return {"narration": f"You attempt to sell {item_name}."}


def scavenge(state: dict[str, Any]) -> dict[str, Any]:
    """Search the area for loose items/currency."""
    roll = random.randint(1, 20)
    if roll >= 15:
        loot = random.randint(1, 10)
        add_currency(state, loot)
        return {"narration": f"You scavenge and find {loot} coins!", "loot": loot}
    return {"narration": "You search but find nothing of value."}
