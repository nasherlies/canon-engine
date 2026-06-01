"""
Canon Engine — Narrator Result Applier

Applies validated narrator results (state_updates) to the game state.
Called after narrate_and_apply returns a result dict.

Public API:
    apply_narrator_result(state, result, turn) -> list[str]
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _try_sync_carry(state: dict) -> None:
    """Call sync_carry if the inventory module is available."""
    try:
        from canon_engine.core.inventory import sync_carry
        sync_carry(state)
    except (ImportError, AttributeError):
        pass


def _try_normalize_item(item: dict) -> dict:
    """Normalize an item dict using the inventory module if available."""
    try:
        from canon_engine.core.inventory import normalize_item
        return normalize_item(item)
    except (ImportError, AttributeError):
        # Minimal normalization fallback
        return {
            "name": str(item.get("name", "Unknown Item")),
            "rarity": str(item.get("rarity", "common")),
        }


def apply_narrator_result(state: dict, result: dict, turn: int = 0) -> List[str]:
    """
    Apply all state_updates from a narrator result to the game state.

    Parameters
    ----------
    state : dict
        The mutable game state dict.
    result : dict
        The validated narrator result (from _validate_result).
    turn : int
        Current turn number (used for logging).

    Returns
    -------
    list[str]
        Log lines describing what was applied, prefixed with [SYSTEM], [CHECK],
        [XP], [LORE], etc.
    """
    log_lines: List[str] = []

    # --- Append narration to world_log ---
    narration = result.get("narration", "")
    if narration:
        world_log = state.setdefault("world_log", [])
        entry = {"turn": turn, "text": narration}
        world_log.append(entry)
        # Also append to command_log for recent-history tracking
        command_log = state.setdefault("command_log", [])
        command_log.append(f"[Turn {turn}] {narration[:200]}")

    # --- Apply check result ---
    check = result.get("check")
    if check and isinstance(check, dict):
        state_check = {
            "turn": turn,
            "type": check.get("type", "ability"),
            "stat": check.get("stat", "STR"),
            "dc": check.get("dc", 10),
            "result": check.get("result", "fail"),
            "roll": check.get("roll", 0),
        }
        checks = state.setdefault("checks", [])
        checks.append(state_check)
        result_str = state_check["result"]
        roll = state_check["roll"]
        dc = state_check["dc"]
        log_lines.append(
            f"[CHECK] {state_check['type'].upper()} {state_check['stat']} "
            f"DC {dc}: rolled {roll} → {result_str}"
        )

    # --- Apply state_updates ---
    su = result.get("state_updates", {})
    if not isinstance(su, dict):
        su = {}

    player = state.setdefault("player", {})

    # HP delta
    hp_delta = su.get("hp_delta", 0)
    if hp_delta:
        current_hp = player.get("hp", 0)
        max_hp = player.get("max_hp", 100)
        new_hp = max(0, min(max_hp, current_hp + hp_delta))
        player["hp"] = new_hp
        direction = "lost" if hp_delta < 0 else "gained"
        log_lines.append(f"[SYSTEM] {direction} {abs(hp_delta)} HP → {new_hp}/{max_hp}")

    # MP delta
    mp_delta = su.get("mp_delta", 0)
    if mp_delta:
        current_mp = player.get("mp", 0)
        max_mp = player.get("max_mp", 50)
        new_mp = max(0, min(max_mp, current_mp + mp_delta))
        player["mp"] = new_mp
        direction = "lost" if mp_delta < 0 else "gained"
        log_lines.append(f"[SYSTEM] {direction} {abs(mp_delta)} MP → {new_mp}/{max_mp}")

    # Stamina delta
    stm_delta = su.get("stm_delta", 0)
    if stm_delta:
        current_stm = player.get("stm", 0)
        max_stm = player.get("max_stm", 100)
        new_stm = max(0, min(max_stm, current_stm + stm_delta))
        player["stm"] = new_stm
        direction = "lost" if stm_delta < 0 else "gained"
        log_lines.append(f"[SYSTEM] {direction} {abs(stm_delta)} STM → {new_stm}/{max_stm}")

    # Gold delta
    gold_delta = su.get("gold_delta", 0)
    if gold_delta:
        current_gold = player.get("gold", 0)
        new_gold = max(0, current_gold + gold_delta)
        player["gold"] = new_gold
        direction = "lost" if gold_delta < 0 else "gained"
        log_lines.append(f"[SYSTEM] {direction} {abs(gold_delta)} gold → {new_gold}")

    # XP (from state_updates.xp_add or top-level xp_add)
    xp_gain = su.get("xp_add", 0) or result.get("xp_add", 0)
    if xp_gain:
        current_xp = player.get("xp", 0)
        player["xp"] = current_xp + xp_gain
        log_lines.append(f"[XP] Gained {xp_gain} XP → {player['xp']} total")

        # Check for level up
        xp_to_next = player.get("xp_to_next", 100)
        if player["xp"] >= xp_to_next:
            player["level"] = player.get("level", 1) + 1
            player["xp"] = player["xp"] - xp_to_next
            player["xp_to_next"] = int(xp_to_next * 1.5)
            log_lines.append(f"[SYSTEM] LEVEL UP! Now level {player['level']}")

    # Inventory add
    inventory_add = su.get("inventory_add", [])
    if inventory_add and isinstance(inventory_add, list):
        inventory = state.setdefault("inventory", [])
        for item in inventory_add:
            if isinstance(item, dict):
                normalized = _try_normalize_item(item)
                inventory.append(normalized)
                log_lines.append(f"[SYSTEM] Acquired: {normalized.get('name', 'Unknown')} ({normalized.get('rarity', 'common')})")
            elif isinstance(item, str):
                inventory.append({"name": item, "rarity": "common"})
                log_lines.append(f"[SYSTEM] Acquired: {item}")

    # Inventory remove
    inventory_remove = su.get("inventory_remove", [])
    if inventory_remove and isinstance(inventory_remove, list):
        inventory = state.get("inventory", [])
        for item_name in inventory_remove:
            for i, inv_item in enumerate(inventory):
                inv_name = inv_item.get("name", "") if isinstance(inv_item, dict) else str(inv_item)
                if inv_name.lower() == item_name.lower():
                    inventory.pop(i)
                    log_lines.append(f"[SYSTEM] Removed: {inv_name}")
                    break

    # Sync carry weight after inventory changes
    if inventory_add or inventory_remove:
        _try_sync_carry(state)

    # Flag set
    flag_set = su.get("flag_set", {})
    if flag_set and isinstance(flag_set, dict):
        flags = state.setdefault("flags", {})
        for key, value in flag_set.items():
            flags[key] = value
            log_lines.append(f"[SYSTEM] Flag set: {key} = {value}")

    # Stat deltas
    stat_deltas = su.get("stat_deltas", {})
    if stat_deltas and isinstance(stat_deltas, dict):
        stats = player.setdefault("stats", {})
        for stat_name, delta in stat_deltas.items():
            delta = int(delta)
            if delta:
                current = stats.get(stat_name, 10)
                stats[stat_name] = current + delta
                direction = "increased" if delta > 0 else "decreased"
                log_lines.append(f"[SYSTEM] {stat_name} {direction} by {abs(delta)} → {stats[stat_name]}")

    # Stat points (unspent points to allocate later)
    stat_points = su.get("stat_points", 0)
    if stat_points:
        current_points = player.get("stat_points", 0)
        player["stat_points"] = current_points + stat_points
        log_lines.append(f"[SYSTEM] Gained {stat_points} stat point(s) → {player['stat_points']} unspent")

    # --- Discovered lore ---
    lore = result.get("discovered_lore")
    if lore and isinstance(lore, dict):
        lore_entries = state.setdefault("lore_entries", [])
        lore_entry = {
            "title": lore.get("title", "Unknown"),
            "category": lore.get("category", "misc"),
            "description": lore.get("description", ""),
            "turn": turn,
        }
        lore_entries.append(lore_entry)
        log_lines.append(f"[LORE] Discovered: {lore_entry['title']} ({lore_entry['category']})")

    # --- Quest update ---
    quest_update = result.get("quest_update")
    if quest_update and isinstance(quest_update, dict):
        quests = state.setdefault("quests", {"active": [], "completed": []})
        action = quest_update.get("action", "progress")
        quest_id = quest_update.get("id", "unknown")

        if action == "new_quest":
            new_quest = {
                "id": quest_id,
                "title": quest_update.get("title", ""),
                "objectives": quest_update.get("objectives", []),
                "turn": turn,
            }
            quests["active"].append(new_quest)
            log_lines.append(f"[SYSTEM] New quest: {new_quest['title']}")
        elif action == "progress":
            for q in quests["active"]:
                if q.get("id") == quest_id:
                    q["objectives"] = quest_update.get("objectives", q.get("objectives", []))
                    log_lines.append(f"[SYSTEM] Quest updated: {q.get('title', quest_id)}")
                    break
        elif action == "complete":
            for i, q in enumerate(quests["active"]):
                if q.get("id") == quest_id:
                    completed = quests["active"].pop(i)
                    quests["completed"].append(completed)
                    log_lines.append(f"[SYSTEM] Quest completed: {completed.get('title', quest_id)}")
                    break

    # --- Saga advance ---
    if result.get("saga_advance"):
        saga = state.setdefault("saga", {})
        saga["turn"] = turn
        saga["milestone"] = True
        log_lines.append("[SYSTEM] ⚡ Saga milestone reached!")

    return log_lines
