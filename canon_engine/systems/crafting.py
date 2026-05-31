"""Recipes, crafting rolls."""

from __future__ import annotations

import random
from typing import Any

# Example recipe registry
RECIPES: dict[str, dict[str, Any]] = {}


def register_recipe(name: str, ingredients: list[str], result: dict[str, Any], dc: int = 10) -> None:
    RECIPES[name] = {"ingredients": ingredients, "result": result, "dc": dc}


def list_recipes() -> list[str]:
    return list(RECIPES.keys())


def attempt_craft(state: dict[str, Any], recipe_name: str) -> dict[str, Any]:
    recipe = RECIPES.get(recipe_name)
    if recipe is None:
        return {"narration": f"Unknown recipe: {recipe_name}", "success": False}
    # Check ingredients (stub — just check they exist in inventory names)
    inv_names = {i.get("name", "").lower() for i in state.get("inventory", [])}
    missing = [ing for ing in recipe["ingredients"] if ing.lower() not in inv_names]
    if missing:
        return {"narration": f"Missing ingredients: {', '.join(missing)}", "success": False}
    # Roll
    roll = random.randint(1, 20)
    if roll >= recipe["dc"]:
        from canon_engine.systems.inventory import add_item
        add_item(state, recipe["result"])
        return {"narration": f"You craft {recipe['result'].get('name', 'an item')}! (rolled {roll})", "success": True}
    return {"narration": f"Crafting failed! (rolled {roll} vs DC {recipe['dc']})", "success": False}


def handle_craft_command(state: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    sub = parsed.get("action", "list")
    if sub == "list":
        return {"narration": f"Known recipes: {', '.join(list_recipes()) or 'none'}"}
    return attempt_craft(state, parsed.get("recipe", ""))
