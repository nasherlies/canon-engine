"""Canon Engine — Crafting System

Recipe-based crafting with DC checks, quality tiers, material consumption,
and time cost.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from canon_engine.core.world import apply_time_passed

# ---------------------------------------------------------------------------
# Content path
# ---------------------------------------------------------------------------

_CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "content"


# ---------------------------------------------------------------------------
# Recipe loading
# ---------------------------------------------------------------------------

def load_recipes() -> list[dict[str, Any]]:
    """Load recipes from content/recipes.json."""
    path = _CONTENT_DIR / "recipes.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("recipes", [])


# ---------------------------------------------------------------------------
# Material checking
# ---------------------------------------------------------------------------

def _get_inventory_materials(state: dict[str, Any]) -> dict[str, int]:
    """Build a {material_name: qty} map from inventory items."""
    mats: dict[str, int] = {}
    for item in state.get("inventory", []):
        if isinstance(item, dict):
            name = item.get("name", "")
            qty = item.get("qty", 1)
            mats[name] = mats.get(name, 0) + qty
        elif isinstance(item, str):
            mats[item] = mats.get(item, 0) + 1
    return mats


def _has_materials(state: dict[str, Any], recipe: dict[str, Any]) -> bool:
    """Check whether the player has all required materials."""
    inv_mats = _get_inventory_materials(state)
    materials = recipe.get("materials", [])
    for mat in materials:
        name = mat.get("name", "")
        qty = mat.get("qty", 1)
        if inv_mats.get(name, 0) < qty:
            return False
    return True


def get_available_recipes(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return recipes where the player currently has all required materials."""
    recipes = load_recipes()
    return [r for r in recipes if _has_materials(state, r)]


# ---------------------------------------------------------------------------
# Material consumption
# ---------------------------------------------------------------------------

def _consume_materials(state: dict[str, Any], recipe: dict[str, Any]) -> list[str]:
    """Remove required materials from inventory. Returns list of consumed names."""
    materials = recipe.get("materials", [])
    consumed: list[str] = []

    for mat in materials:
        name = mat.get("name", "")
        qty_needed = mat.get("qty", 1)
        qty_remaining = qty_needed

        new_inv = []
        found_any = False
        for item in state.get("inventory", []):
            if qty_remaining <= 0:
                new_inv.append(item)
                continue

            if isinstance(item, dict) and item.get("name", "").lower() == name.lower():
                item_qty = item.get("qty", 1)
                if item_qty <= qty_remaining:
                    qty_remaining -= item_qty
                    found_any = True
                    # Don't append — item fully consumed
                else:
                    item["qty"] = item_qty - qty_remaining
                    qty_remaining = 0
                    new_inv.append(item)
                    found_any = True
            elif isinstance(item, str) and item.lower() == name.lower() and qty_remaining > 0:
                qty_remaining -= 1
                found_any = True
            else:
                new_inv.append(item)

        if found_any:
            consumed.append(name)

        state["inventory"] = new_inv

    return consumed


# ---------------------------------------------------------------------------
# Quality tiers
# ---------------------------------------------------------------------------

QUALITY_CRITICAL = "critical_success"
QUALITY_SUCCESS = "success"
QUALITY_PARTIAL = "partial"
QUALITY_FAIL = "fail"


def _determine_quality(roll: int, dc: int) -> str:
    """Determine quality tier from a d20 roll vs DC.

    - Natural 20: critical_success
    - Meet or beat DC: success
    - Fail by less than 3: partial
    - Fail by 3+: fail
    """
    if roll == 20:
        return QUALITY_CRITICAL
    if roll >= dc:
        return QUALITY_SUCCESS
    if dc - roll < 3:
        return QUALITY_PARTIAL
    return QUALITY_FAIL


# ---------------------------------------------------------------------------
# Crafting resolution
# ---------------------------------------------------------------------------

def resolve_craft(
    state: dict[str, Any],
    recipe_id: str,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Attempt to craft an item from a recipe.

    Rolls d20 + INT modifier vs recipe DC.

    Quality tiers:
    - critical_success (nat 20): enhanced item
    - success (meet DC): standard item
    - partial (fail by < 3): damaged version
    - fail (fail by 3+): materials lost, no item

    Returns {ok, quality, item, materials_consumed}.
    """
    _rng = rng or random.Random()

    recipes = load_recipes()
    recipe = None
    for r in recipes:
        if r.get("id") == recipe_id:
            recipe = r
            break

    if recipe is None:
        return {"ok": False, "quality": QUALITY_FAIL, "item": None, "materials_consumed": [], "error": "Recipe not found."}

    if not _has_materials(state, recipe):
        return {"ok": False, "quality": QUALITY_FAIL, "item": None, "materials_consumed": [], "error": "Missing materials."}

    # Consume materials
    consumed = _consume_materials(state, recipe)

    # Roll d20 + INT modifier
    int_stat = state.get("stats", {}).get("INT", 10)
    int_mod = (int_stat - 10) // 2
    roll = _rng.randint(1, 20)
    total = roll + int_mod
    dc = recipe.get("dc", 10)

    quality = _determine_quality(total, dc)

    # Apply time cost
    time_cost = recipe.get("time_cost", 0)
    if time_cost > 0:
        apply_time_passed(state, time_cost)

    result_item = None

    if quality == QUALITY_CRITICAL:
        # Enhanced item — copy result with bonus
        result_item = dict(recipe.get("result", {}))
        result_item["name"] = f"Masterwork {result_item.get('name', 'Item')}"
        result_item["quality"] = "masterwork"

    elif quality == QUALITY_SUCCESS:
        result_item = dict(recipe.get("result", {}))

    elif quality == QUALITY_PARTIAL:
        # Damaged version
        result_item = dict(recipe.get("result", {}))
        result_item["name"] = f"Damaged {result_item.get('name', 'Item')}"
        result_item["quality"] = "damaged"
        result_item["rarity"] = "common"

    else:
        # Fail — materials lost
        return {
            "ok": False,
            "quality": QUALITY_FAIL,
            "item": None,
            "materials_consumed": consumed,
            "roll": roll,
            "total": total,
            "dc": dc,
            "description": f"Crafting failed! (Rolled {total} vs DC {dc}). Materials are lost.",
        }

    # Add item to inventory
    if result_item:
        state.setdefault("inventory", []).append(result_item)

    return {
        "ok": True,
        "quality": quality,
        "item": result_item,
        "materials_consumed": consumed,
        "roll": roll,
        "total": total,
        "dc": dc,
        "description": f"Crafted **{result_item.get('name', 'item')}** [{quality}].",
    }


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def format_recipe_list(recipes: list[dict[str, Any]]) -> str:
    """Format a list of recipes for display."""
    if not recipes:
        return "No recipes available."

    lines = ["**Available Recipes**", ""]
    for r in recipes:
        name = r.get("name", "Unknown")
        rid = r.get("id", "?")
        dc = r.get("dc", "?")
        mats = ", ".join(
            f"{m.get('name', '?')}×{m.get('qty', 1)}"
            for m in r.get("materials", [])
        )
        lines.append(f"- **{name}** (id: `{rid}`) — DC {dc}")
        lines.append(f"  Materials: {mats}")
    return "\n".join(lines)
