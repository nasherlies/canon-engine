"""Canon Engine core — the main game loop.

step_session_turn is ONE HEARTBEAT: parse → guards → turn counter →
apply command → quests tick → world clock → autosave hooks → memory refresh.
"""

from __future__ import annotations

import logging
from typing import Any

from canon_engine.config import Config
from canon_engine.state_manager import save_state, autosave

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def step_session_turn(
    state: dict[str, Any],
    parsed_command: dict[str, Any],
    *,
    narrator=None,
    config: Config | None = None,
) -> dict[str, Any]:
    """Execute one game-turn heartbeat.

    Parameters
    ----------
    state : dict
        The full mutable game state dict.
    parsed_command : dict
        Output of ``command_parser.parse_command``. Must contain at least
        a ``'kind'`` key.
    narrator : optional
        Narrator object used for AI-generated text.  ``None`` means skip
        narration.
    config : optional
        Runtime config. Falls back to ``Config()`` if omitted.

    Returns
    -------
    dict
        Response dict with keys: ``narration``, ``layout``, ``state_delta``,
        ``dirty`` (bool).
    """
    config = config or Config()

    # 1. Pre-flight guards (combat, encounter, etc.)
    guard_result = _run_guards(state, parsed_command)
    if guard_result is not None:
        return guard_result

    # 2. Increment turn counter
    state.setdefault("turn", 0)
    state["turn"] += 1

    # 3. Apply the parsed command
    apply_result = _apply_parsed(state, parsed_command, narrator=narrator)

    # 4. Quest tick
    from canon_engine.systems.quests import tick_quests
    quest_events = tick_quests(state)

    # 5. World clock advance
    from canon_engine.systems.world import apply_time_passed
    time_delta = apply_time_passed(state, parsed_command)

    # 6. Autosave hooks
    if apply_result.get("dirty", True):
        _maybe_autosave(state, config)

    # 7. Memory refresh hook
    _refresh_memory(state)

    # Merge quest events into narration
    narration = apply_result.get("narration", "")
    if quest_events:
        narration = f"{narration}\n\n{''.join(quest_events)}".strip()

    return {
        "narration": narration,
        "layout": apply_result.get("layout", {}),
        "state_delta": apply_result.get("state_delta", {}),
        "dirty": True,
        "turn": state["turn"],
    }


# ---------------------------------------------------------------------------
# Internal dispatch
# ---------------------------------------------------------------------------

def _apply_parsed(
    state: dict[str, Any],
    parsed: dict[str, Any],
    *,
    narrator=None,
) -> dict[str, Any]:
    """Large if/elif dispatch based on parsed['kind']."""
    kind = parsed.get("kind", "unknown")

    if kind == "say":
        text = narrator.narrate(parsed.get("text", ""), state) if narrator else parsed.get("text", "")
        return {"narration": text, "dirty": True}

    if kind == "do":
        text = narrator.narrate(parsed.get("text", ""), state) if narrator else parsed.get("text", "")
        return {"narration": text, "dirty": True}

    if kind == "look":
        from canon_engine.systems.world import describe_location
        desc = describe_location(state)
        return {"narration": desc, "dirty": False}

    if kind == "move":
        from canon_engine.systems.world import move_player
        result = move_player(state, parsed.get("direction", ""))
        return {"narration": result.get("narration", ""), "dirty": True, "layout": result.get("layout", {})}

    if kind == "attack":
        from canon_engine.systems.combat import resolve_player_attack
        result = resolve_player_attack(state, parsed)
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "block":
        from canon_engine.systems.combat import resolve_player_dodge
        result = resolve_player_dodge(state)
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "dodge":
        from canon_engine.systems.combat import resolve_player_dodge
        result = resolve_player_dodge(state)
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "turn":
        from canon_engine.systems.combat import resolve_turn_status
        result = resolve_turn_status(state)
        return {"narration": result.get("narration", ""), "dirty": False}

    if kind == "saving_throw":
        from canon_engine.systems.combat import resolve_saving_throw
        result = resolve_saving_throw(state, parsed)
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "flee":
        from canon_engine.systems.combat import resolve_combat_flee
        result = resolve_combat_flee(state)
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "inventory":
        from canon_engine.systems.inventory import get_inventory_summary
        return {"narration": get_inventory_summary(state), "dirty": False}

    if kind == "equip":
        from canon_engine.systems.inventory import equip_item
        result = equip_item(state, parsed.get("item", ""))
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "unequip":
        from canon_engine.systems.inventory import unequip_item
        result = unequip_item(state, parsed.get("slot", ""))
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "buy":
        from canon_engine.systems.economy import buy_item
        result = buy_item(state, parsed.get("item", ""), parsed.get("vendor", ""))
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "sell":
        from canon_engine.systems.economy import sell_item
        result = sell_item(state, parsed.get("item", ""), parsed.get("vendor", ""))
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "rest":
        from canon_engine.systems.rest import short_rest
        result = short_rest(state)
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "sleep":
        from canon_engine.systems.rest import long_rest
        result = long_rest(state)
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "quest":
        from canon_engine.systems.quests import handle_quest_command
        result = handle_quest_command(state, parsed)
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "skill":
        from canon_engine.systems.skills import handle_skill_command
        result = handle_skill_command(state, parsed)
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "craft":
        from canon_engine.systems.crafting import handle_craft_command
        result = handle_craft_command(state, parsed)
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "scout":
        from canon_engine.systems.stealth import scout_area
        result = scout_area(state)
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "talk":
        from canon_engine.systems.npcs import handle_talk
        result = handle_talk(state, parsed.get("npc", ""))
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "companion":
        from canon_engine.systems.companions import handle_companion_command
        result = handle_companion_command(state, parsed)
        return {"narration": result.get("narration", ""), "dirty": True}

    if kind == "status":
        from canon_engine.systems.status import get_active_effects
        effects = get_active_effects(state)
        return {"narration": f"Active effects: {effects}", "dirty": False}

    if kind == "lore":
        from canon_engine.systems.lore import query_lore
        result = query_lore(state, parsed.get("query", ""))
        return {"narration": result.get("narration", ""), "dirty": False}

    # Unknown / pass-through
    text = narrator.narrate(parsed.get("text", str(parsed)), state) if narrator else str(parsed)
    return {"narration": text, "dirty": True}


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

def _run_guards(state: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any] | None:
    """Pre-flight guards.  Return a response dict to short-circuit, or None."""
    # During active combat only combat commands are allowed
    if state.get("combat", {}).get("active"):
        allowed = {"attack", "block", "dodge", "flee", "use_item", "status", "turn", "saving_throw"}
        if parsed.get("kind") not in allowed:
            return {
                "narration": "You're in the middle of combat! You can attack, dodge, flee, turn, or use an item.",
                "layout": {},
                "state_delta": {},
                "dirty": False,
            }
    return None


# ---------------------------------------------------------------------------
# Autosave / memory
# ---------------------------------------------------------------------------

def _maybe_autosave(state: dict[str, Any], config: Config) -> None:
    """Trigger autosave if conditions are met."""
    is_tutorial = state.get("run_mode") == "tutorial"
    autosave(state, is_tutorial=is_tutorial)


def _refresh_memory(state: dict[str, Any]) -> None:
    """Hook for refreshing short-term memory / summarisation."""
    logger.debug("Memory refresh at turn %s", state.get("turn"))
