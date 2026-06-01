"""Game session – the main interactive loop for Canon Engine.

This module owns the *single source of truth* for what players can do during
a session.  It takes parsed commands (from ``core.command_parser``), applies
them to the game state via ``_apply_parsed``, and returns narration + layout
data for the UI layer.

Public API
----------
* ``step_session_turn(state, command, rng, character, ...)`` – central orchestrator.
* ``build_layout_payload(state, narration, combat_active)`` – full HUD payload.
* ``GameSession`` – wraps state, engine, and UI concerns.
* ``GameSession.run()`` – blocking TUI loop (Rich terminal).
* ``GameSession.handle_command(text)`` – single command turn (for API use).
"""

from __future__ import annotations

import logging
import random as _random
from typing import Any, Dict, Optional

from canon_engine import state_manager
from canon_engine.config import Config
from canon_engine.constants import ENGINE_NAME

logger = logging.getLogger(__name__)


# ── Stub helpers for modules that may not exist yet ──────────────────────────

def _safe_import(module_path: str, attr: str | None = None) -> Any:
    """Import *module_path* and optionally return *attr*.  Returns None on failure."""
    try:
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, attr) if attr else mod
    except (ImportError, AttributeError):
        return None


# Lazy references (resolved at call time, not import time)
_narrate = None
_step_turn = None


def _get_narrate():
    """Return the narration function, or a stub if narrator module is missing."""
    global _narrate
    if _narrate is None:
        fn = _safe_import("canon_engine.narrator", "narrate")
        if fn is None:
            fn = _safe_import("canon_engine.narrator", "generate_narration")
        if fn is None:
            def _stub_narrate(state: dict, command: dict, **kw) -> str:
                kind = command.get("kind", "unknown")
                return f"[The narrator is silent. You attempted: /{kind}]"
            _narrate = _stub_narrate
        else:
            _narrate = fn
    return _narrate


def _get_step_turn():
    """Return the engine step function, or a stub."""
    global _step_turn
    if _step_turn is None:
        fn = _safe_import("canon_engine.engine", "step_session_turn")
        if fn is None:
            def _stub_step(state: dict, parsed: dict, **kw) -> dict:
                return {"state_delta": {}, "narration": "", "events": []}
            _step_turn = _stub_step
        else:
            _step_turn = fn
    return _step_turn


# ═══════════════════════════════════════════════════════════════════════════════
# CENTRAL ORCHESTRATOR — step_session_turn
# ═══════════════════════════════════════════════════════════════════════════════

# Commands allowed inside the combat shell
_COMBAT_ALLOWED = frozenset({
    "attack", "block", "item", "flee", "turn", "look", "look_enemies",
    "help", "save", "load", "quit",
})

# Utility commands that get 5 min world-time advance
_UTILITY_KINDS = frozenset({
    "say", "do", "think", "look", "inv", "inspect", "use", "equip",
    "drop", "combine", "give", "talk", "save", "load", "quicksave",
    "help", "stats", "addstat", "levelup", "skills", "unlock",
    "factions", "craft", "shop", "buy", "sell", "barter", "rent",
    "scavenge", "map", "lore", "quests", "quest", "accept", "abandon",
    "turnin", "npcs", "npc", "gift", "threaten", "recruit", "dismiss",
    "companion", "order", "lockpick", "gamble", "choices", "collide",
    "summary", "encounter", "menu", "quit", "soul", "admin", "retcon",
    "start_character",
})


def step_session_turn(
    state: dict,
    command: str,
    rng: _random.Random,
    character: dict | None = None,
    *,
    lock_world_time_from_llm: bool = False,
) -> dict:
    """
    Central orchestrator: parse a command, dispatch to the right module,
    apply post-turn bookkeeping, and return the result payload.

    Parameters
    ----------
    state : dict
        Mutable game state.
    command : str
        Raw player command text (e.g. "/say hello", "look around").
    rng : random.Random
        Seeded RNG for deterministic results.
    character : dict, optional
        If provided, rebuild state from character creation data first.
    lock_world_time_from_llm : bool
        If True, LLM time suggestions override world clock.

    Returns
    -------
    dict
        {ok: bool, narration: str, command_log: list, layout: dict}
    """
    from canon_engine.core.command_parser import parse_command
    from canon_engine.core.character_session import build_character_session_state
    from canon_engine.core.narrator import narrate_and_apply
    from canon_engine.core.narrator_apply import apply_narrator_result
    from canon_engine.core.leveling import grant_turn_xp
    from canon_engine.core.memory_warm import maybe_update_memory
    from canon_engine.core.status import tick_statuses
    from canon_engine.core.world import ensure_world, advance_world_time

    # 1. If character provided, rebuild state
    if character:
        fresh = build_character_session_state(character)
        state.clear()
        state.update(fresh)

    # Ensure world state exists
    ensure_world(state)

    # 2. Parse command
    kind, args = parse_command(command)

    # 3. Combat shell gate
    combat = state.get("combat", {})
    in_combat = bool(combat.get("active", False))
    if in_combat and kind not in _COMBAT_ALLOWED:
        return {
            "ok": True,
            "narration": "⚔ You're in combat! Use /attack, /block, /item, /flee, /turn, or /help.",
            "command_log": state.get("command_log", []),
            "layout": build_layout_payload(state, combat_active=True),
        }

    # 4. Dispatch
    narration = ""
    narrator_result = None

    try:
        narration, narrator_result = _dispatch_command(
            state, kind, args, command, rng, lock_world_time_from_llm,
        )
    except Exception as exc:
        logger.exception("Error dispatching command %s", kind)
        narration = f"❌ An error occurred: {exc}"

    # 5. Post-turn bookkeeping
    turn = state.get("turn", 0)

    # Apply narrator result if we have one
    if narrator_result:
        apply_narrator_result(state, narrator_result, turn)
        maybe_update_memory(state, narrator_result, turn)

    # Grant turn XP
    grant_turn_xp(state, kind)

    # Tick non-combat statuses (travel trigger)
    tick_statuses(state, "travel", rng)

    # Advance world time for utility commands
    if kind in _UTILITY_KINDS and kind not in ("save", "load", "quicksave", "help", "menu", "quit"):
        advance_world_time(state, 5)

    # Increment turn counter
    state["turn"] = turn + 1

    # 6. Autosave
    try:
        state_manager.autosave(state)
    except Exception as exc:
        logger.debug("Autosave skipped: %s", exc)

    # 7. Build and return result
    # Append to command log
    state.setdefault("command_log", []).append(f"[Turn {turn}] /{kind}")

    layout = build_layout_payload(state, narration=narration, combat_active=in_combat)

    return {
        "ok": True,
        "narration": narration,
        "command_log": state.get("command_log", []),
        "layout": layout,
    }


def _dispatch_command(
    state: dict,
    kind: str,
    args: dict,
    raw_command: str,
    rng: _random.Random,
    lock_world_time_from_llm: bool = False,
) -> tuple[str, dict | None]:
    """
    Dispatch a parsed command to the appropriate handler.

    Returns (narration_text, narrator_result_or_None).
    """
    from canon_engine.core.narrator import narrate_and_apply
    from canon_engine.core.combat import (
        resolve_attack, resolve_block, resolve_combat_item, resolve_flee,
        format_combat_banner, format_combat_enemies_look, start_combat,
        end_combat, check_combat_end, combat_open_player_tick, combat_enemy_phase,
    )
    from canon_engine.core.encounter_bridge import (
        start_encounter, resolve_talk, resolve_flee_encounter, transition_to_combat,
    )
    from canon_engine.core.inventory import (
        format_inventory_sheet, format_inventory_rows, equip_item, use_item,
        drop_item, combine_items, give_item, normalize_item,
    )
    from canon_engine.core.leveling import apply_level_up, format_levelup_display
    from canon_engine.core.skills import resolve_unlock, get_available_skills
    from canon_engine.core.world import clock_line, sky, get_weather_display
    from canon_engine.core.status import tick_statuses, apply_status

    combat = state.get("combat", {})
    in_combat = bool(combat.get("active", False))
    encounter_status = state.get("encounter_status", "none")
    in_encounter = encounter_status == "standoff"

    # ── say, do, think: route through narrate_and_apply ────────────────
    if kind in ("say", "do", "think"):
        player_input = args.get("words", "")
        if kind == "think":
            player_input = f"/think {player_input}"
        elif kind == "do":
            player_input = f"/do {player_input}"
        result = narrate_and_apply(
            state, player_input,
            turn=state.get("turn", 0), rng=rng,
            lock_world_time_from_llm=lock_world_time_from_llm,
        )
        return result.get("narration", ""), result

    # ── look ───────────────────────────────────────────────────────────
    if kind == "look":
        if in_combat:
            return format_combat_enemies_look(state), None
        result = narrate_and_apply(
            state, "/do Look around carefully",
            turn=state.get("turn", 0), rng=rng,
        )
        return result.get("narration", ""), result

    # ── look_enemies (combat only) ─────────────────────────────────────
    if kind == "look_enemies":
        if in_combat:
            return format_combat_enemies_look(state), None
        return "No enemies to look at.", None

    # ── inv ────────────────────────────────────────────────────────────
    if kind == "inv":
        return format_inventory_sheet(state), None

    # ── inspect ────────────────────────────────────────────────────────
    if kind == "inspect":
        item_name = args.get("item", "")
        from canon_engine.core.inventory import _find_item
        idx, item = _find_item(state, item_name)
        if item is None:
            return f"You don't have '{item_name}'.", None
        lines = [f"**{item.get('name', 'Unknown')}**"]
        lines.append(f"  Rarity: {item.get('rarity', 'common')}")
        lines.append(f"  Type: {item.get('itype', 'misc')}")
        if item.get("equip_slot"):
            lines.append(f"  Slot: {item.get('equip_slot')}")
        if item.get("effects"):
            lines.append(f"  Effects: {item.get('effects')}")
        if item.get("lore"):
            lines.append(f"  Lore: {item.get('lore')}")
        lines.append(f"  Weight: {item.get('weight', 0)}")
        lines.append(f"  Qty: {item.get('qty', 1)}")
        return "\n".join(lines), None

    # ── use ────────────────────────────────────────────────────────────
    if kind == "use":
        result = use_item(state, args.get("item", ""), rng)
        return result.get("message", ""), None

    # ── equip ──────────────────────────────────────────────────────────
    if kind == "equip":
        result = equip_item(state, args.get("item", ""))
        return result.get("message", ""), None

    # ── drop ───────────────────────────────────────────────────────────
    if kind == "drop":
        result = drop_item(state, args.get("item", ""))
        return result.get("message", ""), None

    # ── combine ────────────────────────────────────────────────────────
    if kind == "combine":
        result = combine_items(state, args.get("item1", ""), args.get("item2", ""), rng)
        return result.get("message", ""), None

    # ── give ───────────────────────────────────────────────────────────
    if kind == "give":
        result = give_item(state, args.get("item", ""), args.get("recipient", ""))
        return result.get("message", ""), None

    # ── attack ─────────────────────────────────────────────────────────
    if kind == "attack":
        if in_combat:
            target = args.get("target", "")
            # Try to parse as index
            try:
                target_idx = int(target) if target else 0
            except ValueError:
                # Find by name
                target_idx = 0
                for i, e in enumerate(combat.get("enemies", [])):
                    if target.lower() in e.get("display_name", e.get("type", "")).lower():
                        target_idx = i
                        break

            # Player tick
            msgs = combat_open_player_tick(state, rng)
            result = resolve_attack(state, target_idx, rng)
            narration_parts = msgs + [result.get("description", "")]

            # Check if all enemies dead
            end_status = check_combat_end(state)
            if end_status == "victory":
                end_result = end_combat(state, rng)
                narration_parts.append(f"🏆 Victory! Gained {end_result.get('xp', 0)} XP and {end_result.get('gold', 0)} gold.")
            elif end_status == "defeat":
                narration_parts.append("💀 You have been defeated!")
                combat["active"] = False
            else:
                # Enemy phase
                enemy_msgs = combat_enemy_phase(state, rng)
                narration_parts.extend(enemy_msgs)
                # Check again after enemy phase
                end_status = check_combat_end(state)
                if end_status == "defeat":
                    narration_parts.append("💀 You have been defeated!")
                    combat["active"] = False

            return "\n".join(narration_parts), None
        else:
            return "You're not in combat. Use /fight or /encounter to start one.", None

    # ── block ──────────────────────────────────────────────────────────
    if kind == "block":
        if in_combat:
            result = resolve_block(state)
            # Enemy phase
            enemy_msgs = combat_enemy_phase(state, rng)
            return result.get("description", "") + "\n" + "\n".join(enemy_msgs), None
        return "You're not in combat.", None

    # ── item (combat use) ─────────────────────────────────────────────
    if kind == "item":
        if in_combat:
            result = resolve_combat_item(state, args.get("name", ""), rng)
            return result.get("description", ""), None
        return "You're not in combat. Use /use outside combat.", None

    # ── flee ───────────────────────────────────────────────────────────
    if kind == "flee":
        if in_combat:
            result = resolve_flee(state, rng)
            return result.get("description", ""), None
        if in_encounter:
            result = resolve_flee_encounter(state, rng)
            return result.get("description", ""), None
        return "Nothing to flee from.", None

    # ── fight ──────────────────────────────────────────────────────────
    if kind == "fight":
        if in_combat:
            return "You're already in combat!", None
        if in_encounter:
            transition_to_combat(state, rng)
            pending = state.get("pending_encounter", {})
            enemies = pending.get("enemies", [])
            start_combat(state, {"enemies": enemies}, rng)
            names = ", ".join(e.get("type", "enemy") for e in enemies)
            return f"⚔ Combat begins! Facing: {names}\n\n" + format_combat_banner(state), None
        return "Nothing to fight. Use /encounter to find enemies.", None

    # ── talk ───────────────────────────────────────────────────────────
    if kind == "talk":
        if in_encounter:
            result = resolve_talk(state, rng)
            return result.get("description", ""), None
        # Narrate as a say action
        player_input = f"/say {args.get('words', '')}"
        result = narrate_and_apply(state, player_input, turn=state.get("turn", 0), rng=rng)
        return result.get("narration", ""), result

    # ── turn ───────────────────────────────────────────────────────────
    if kind == "turn":
        if in_combat:
            return format_combat_banner(state), None
        return "You're not in combat.", None

    # ── save ───────────────────────────────────────────────────────────
    if kind == "save":
        slot = args.get("slot", "default")
        try:
            state_manager.save_state(state, slot)
            return f"💾 Saved to slot '{slot}'.", None
        except Exception as exc:
            return f"❌ Save failed: {exc}", None

    # ── load ───────────────────────────────────────────────────────────
    if kind == "load":
        slot = args.get("slot", "default")
        try:
            loaded = state_manager.load_state(slot)
            state.clear()
            state.update(loaded)
            return f"📂 Loaded save '{slot}'.", None
        except Exception as exc:
            return f"❌ Load failed: {exc}", None

    # ── quicksave ──────────────────────────────────────────────────────
    if kind == "quicksave":
        try:
            state_manager.save_state(state, "quicksave")
            return "💾 Quicksave complete.", None
        except Exception as exc:
            return f"❌ Quicksave failed: {exc}", None

    # ── help ───────────────────────────────────────────────────────────
    if kind == "help":
        topic = args.get("topic", "")
        if topic:
            return _handle_help_topic(topic), None
        return _handle_help_general(), None

    # ── menu / quit ────────────────────────────────────────────────────
    if kind in ("menu", "quit"):
        return "Session ended. Farewell, adventurer.", None

    # ── stats ──────────────────────────────────────────────────────────
    if kind == "stats":
        player = state.get("player", state)
        stats = player.get("stats", {})
        name = player.get("name", "Adventurer")
        level = player.get("level", 1)
        hp = player.get("hp", 0)
        max_hp = player.get("max_hp", hp)
        mp = player.get("mp", 0)
        max_mp = player.get("max_mp", mp)
        stm = player.get("stm", player.get("stamina", 0))
        max_stm = player.get("max_stm", player.get("max_stamina", stm))
        xp = player.get("xp", 0)
        xp_next = player.get("xp_to_next", player.get("xp_next", 100))
        gold = player.get("gold", 0)

        lines = [
            f"**{name}** — Level {level}",
            f"HP: {hp}/{max_hp}  |  MP: {mp}/{max_mp}  |  STM: {stm}/{max_stm}",
            f"XP: {xp}/{xp_next}  |  Gold: {gold}",
            "",
            "**Stats:**",
        ]
        for stat in ("STR", "DEX", "INT", "CHA", "CON", "LCK"):
            val = stats.get(stat, 10)
            mod = (val - 10) // 2
            sign = "+" if mod >= 0 else ""
            lines.append(f"  {stat}: {val} ({sign}{mod})")

        sp = player.get("stat_points", 0) or state.get("stat_points", 0)
        if sp:
            lines.append(f"\nUnspent stat points: {sp}")

        return "\n".join(lines), None

    # ── addstat ────────────────────────────────────────────────────────
    if kind == "addstat":
        stat = args.get("stat", "").upper()
        if stat not in ("STR", "DEX", "INT", "CHA", "CON", "LCK"):
            return f"Unknown stat '{stat}'. Valid: STR, DEX, INT, CHA, CON, LCK.", None
        player = state.get("player", state)
        sp = player.get("stat_points", 0) or state.get("stat_points", 0)
        if sp <= 0:
            return "No stat points available. Level up first!", None
        stats = player.get("stats", {})
        stats[stat] = stats.get(stat, 10) + 1
        if "stat_points" in player:
            player["stat_points"] -= 1
        else:
            state["stat_points"] = sp - 1
        return f"✨ {stat} increased to {stats[stat]}! ({sp - 1} points remaining)", None

    # ── levelup ────────────────────────────────────────────────────────
    if kind == "levelup":
        result = apply_level_up(state)
        return result.get("message", ""), None

    # ── skills ─────────────────────────────────────────────────────────
    if kind == "skills":
        try:
            available = get_available_skills(state)
            player = state.get("player", state)
            unlocked = state.get("unlocked_skills", player.get("skills", []))
            points = state.get("skill_points", player.get("skill_points", 0))
            lines = [f"**Skills** (Points: {points}):"]
            if unlocked:
                lines.append("Unlocked: " + ", ".join(str(s) for s in unlocked))
            if available:
                lines.append("\nAvailable to unlock:")
                for s in available:
                    lines.append(f"  • {s.get('name', s.get('id', '?'))} (cost: {s.get('cost', 1)})")
            else:
                lines.append("No skills available to unlock.")
            return "\n".join(lines), None
        except Exception:
            return "🎯 Skills system not available.", None

    # ── unlock ─────────────────────────────────────────────────────────
    if kind == "unlock":
        skill_id = args.get("skill_id", "")
        result = resolve_unlock(state, skill_id)
        return result.get("message", ""), None

    # ── factions ───────────────────────────────────────────────────────
    if kind == "factions":
        try:
            from canon_engine.core.factions import ensure_factions, FACTION_TIERS
            facs = ensure_factions(state)
            if not facs:
                return "🏴 No known factions.", None
            lines = ["**Factions:**"]
            for fid, fdata in facs.items():
                rep = fdata.get("reputation", 0) if isinstance(fdata, dict) else 0
                tier = "neutral"
                for t_name, t_lo, t_hi in FACTION_TIERS:
                    if t_lo <= rep < t_hi:
                        tier = t_name
                        break
                lines.append(f"  • {fid}: {rep} ({tier})")
            return "\n".join(lines), None
        except Exception:
            return "🏴 Factions system not available.", None

    # ── craft ──────────────────────────────────────────────────────────
    if kind == "craft":
        try:
            from canon_engine.core.crafting import resolve_craft, get_available_recipes, format_recipe_list
            craft_id = args.get("id", "list")
            if craft_id == "list":
                recipes = get_available_recipes(state)
                return format_recipe_list(recipes), None
            result = resolve_craft(state, craft_id, rng)
            return result.get("message", result.get("narration", "")), None
        except Exception:
            return "🔧 Crafting system not available.", None

    # ── shop ───────────────────────────────────────────────────────────
    if kind == "shop":
        try:
            from canon_engine.core.economy import format_shop
            return format_shop(state), None
        except Exception:
            return "🏪 No shops available here.", None

    # ── buy ────────────────────────────────────────────────────────────
    if kind == "buy":
        try:
            from canon_engine.core.economy import resolve_buy
            result = resolve_buy(state, args.get("item", ""), None, rng)
            return result.get("message", ""), None
        except Exception:
            return "🏪 Buy system not available.", None

    # ── sell ───────────────────────────────────────────────────────────
    if kind == "sell":
        try:
            from canon_engine.core.economy import resolve_sell
            result = resolve_sell(state, args.get("item", ""))
            return result.get("message", ""), None
        except Exception:
            return "🏪 Sell system not available.", None

    # ── barter ─────────────────────────────────────────────────────────
    if kind == "barter":
        try:
            from canon_engine.core.economy import resolve_barter
            result = resolve_barter(state, "", rng)
            return result.get("message", result.get("description", "")), None
        except Exception:
            return "💰 Barter system not available.", None

    # ── rent ───────────────────────────────────────────────────────────
    if kind == "rent":
        try:
            from canon_engine.core.economy import resolve_rent
            result = resolve_rent(state)
            return result.get("message", ""), None
        except Exception:
            return "🏨 No inn available.", None

    # ── scavenge ───────────────────────────────────────────────────────
    if kind == "scavenge":
        try:
            from canon_engine.core.economy import resolve_scavenge
            result = resolve_scavenge(state, rng)
            return result.get("message", result.get("description", "")), None
        except Exception:
            return "🔍 Nothing to scavenge here.", None

    # ── nap / sleep ────────────────────────────────────────────────────
    if kind in ("nap", "sleep"):
        try:
            from canon_engine.core.recovery import resolve_nap, resolve_sleep
            if kind == "nap":
                result = resolve_nap(state, rng)
            else:
                result = resolve_sleep(state, rng)
            return result.get("message", result.get("narration", "")), None
        except Exception:
            return "💤 Recovery system not available.", None

    # ── travel ─────────────────────────────────────────────────────────
    if kind == "travel":
        try:
            from canon_engine.core.travel import apply_engine_travel
            dest = args.get("destination", "")
            result = apply_engine_travel(state, dest, rng)
            return result.get("message", result.get("narration", "")), None
        except Exception:
            return f"🚂 Can't travel to '{args.get('destination', '')}'.", None

    # ── scout / stealth ────────────────────────────────────────────────
    if kind in ("scout", "stealth"):
        try:
            from canon_engine.core.stealth import resolve_scout, resolve_stealth
            if kind == "scout":
                result = resolve_scout(state, rng)
            else:
                result = resolve_stealth(state, rng)
            return result.get("message", result.get("description", "")), None
        except Exception:
            return "🔍 Stealth system not available.", None

    # ── cover / climb ──────────────────────────────────────────────────
    if kind in ("cover", "climb"):
        try:
            from canon_engine.core.terrain import resolve_cover, resolve_climb
            if kind == "cover":
                result = resolve_cover(state)
            else:
                result = resolve_climb(state, rng)
            return result.get("message", result.get("description", "")), None
        except Exception:
            return "🏔 Terrain system not available.", None

    # ── map ────────────────────────────────────────────────────────────
    if kind == "map":
        try:
            from canon_engine.core.worldgen import format_map
            return format_map(state), None
        except Exception:
            world = state.get("world", {})
            loc = world.get("location_name", world.get("location_id", "Unknown"))
            return f"📍 Current location: {loc}\nNo map data available.", None

    # ── lore ───────────────────────────────────────────────────────────
    if kind == "lore":
        topic = args.get("topic", "")
        try:
            from canon_engine.core.item_lore import get_item_lore
            lore = get_item_lore(topic)
            if lore:
                return f"📖 **{topic}**: {lore}", None
        except Exception:
            pass
        # Check lore_entries in state
        for entry in state.get("lore_entries", []):
            if topic.lower() in entry.get("title", "").lower():
                return f"📖 **{entry['title']}**: {entry.get('description', '')}", None
        return f"📖 No lore found for '{topic}'.", None

    # ── quests ─────────────────────────────────────────────────────────
    if kind == "quests":
        quests = state.get("quests", {})
        if isinstance(quests, dict):
            active = quests.get("active", [])
            completed = quests.get("completed", [])
        elif isinstance(quests, list):
            active = quests
            completed = []
        else:
            return "📜 No quests.", None

        if not active and not completed:
            return "📜 No active quests.", None
        lines = []
        if active:
            lines.append("**Active Quests:**")
            for q in active:
                title = q.get("title", q.get("name", "Unknown"))
                lines.append(f"  • {title}")
        if completed:
            lines.append(f"\n**Completed:** {len(completed)}")
        return "\n".join(lines), None

    # ── quest ──────────────────────────────────────────────────────────
    if kind == "quest":
        qid = args.get("id", "")
        quests = state.get("quests", {})
        all_quests = (quests.get("active", []) + quests.get("completed", [])) if isinstance(quests, dict) else quests
        for q in all_quests:
            if q.get("id") == qid or q.get("title", "").lower() == qid.lower():
                lines = [f"**{q.get('title', q.get('name', 'Unknown'))}**"]
                if q.get("objectives"):
                    for obj in q["objectives"]:
                        lines.append(f"  • {obj}")
                if q.get("description"):
                    lines.append(f"\n{q['description']}")
                return "\n".join(lines), None
        return f"📜 Quest '{qid}' not found.", None

    # ── accept / abandon / turnin ──────────────────────────────────────
    if kind in ("accept", "abandon", "turnin"):
        qid = args.get("id", "")
        quests = state.setdefault("quests", {"active": [], "completed": []})
        if isinstance(quests, list):
            state["quests"] = {"active": quests, "completed": []}
            quests = state["quests"]

        if kind == "accept":
            return f"📜 Quest '{qid}' accepted. (Quest system requires narrator integration)", None
        elif kind == "abandon":
            for i, q in enumerate(quests.get("active", [])):
                if q.get("id") == qid:
                    quests["active"].pop(i)
                    return f"📜 Quest '{qid}' abandoned.", None
            return f"📜 Quest '{qid}' not found.", None
        elif kind == "turnin":
            for i, q in enumerate(quests.get("active", [])):
                if q.get("id") == qid:
                    completed = quests["active"].pop(i)
                    quests.setdefault("completed", []).append(completed)
                    return f"📜 Quest '{qid}' completed!", None
            return f"📜 Quest '{qid}' not found.", None

    # ── npcs ───────────────────────────────────────────────────────────
    if kind == "npcs":
        try:
            from canon_engine.core.npc import format_npcs_here
            return format_npcs_here(state), None
        except Exception:
            return "👥 No NPCs nearby.", None

    # ── npc ────────────────────────────────────────────────────────────
    if kind == "npc":
        try:
            from canon_engine.core.npc import get_npc, format_npc_sheet
            npc_id = args.get("id", "")
            npc = get_npc(state, npc_id)
            if npc:
                return format_npc_sheet(npc), None
            return f"👥 NPC '{npc_id}' not found.", None
        except Exception:
            return "👥 NPC system not available.", None

    # ── gift ───────────────────────────────────────────────────────────
    if kind == "gift":
        try:
            from canon_engine.core.npc import apply_relationship_delta
            item_name = args.get("item", "")
            npc_id = args.get("npc", "")
            # Remove item from inventory
            from canon_engine.core.inventory import _find_item
            idx, item = _find_item(state, item_name)
            if item is None:
                return f"You don't have '{item_name}'.", None
            state["inventory"].pop(idx)
            apply_relationship_delta(state, npc_id, 5)
            return f"🎁 Gave {item_name} to {npc_id}. (+5 relationship)", None
        except Exception:
            return "🎁 Gift system not available.", None

    # ── threaten ───────────────────────────────────────────────────────
    if kind == "threaten":
        try:
            from canon_engine.core.npc import apply_relationship_delta
            npc_id = args.get("npc", "")
            apply_relationship_delta(state, npc_id, -10)
            return f"😠 You threaten {npc_id}. (-10 relationship)", None
        except Exception:
            return "😠 Threaten system not available.", None

    # ── recruit ────────────────────────────────────────────────────────
    if kind == "recruit":
        try:
            from canon_engine.systems.companions import recruit
            npc_id = args.get("npc", "")
            from canon_engine.core.npc import get_npc
            npc = get_npc(state, npc_id) or {"name": npc_id}
            result = recruit(state, npc)
            return result.get("narration", ""), None
        except Exception:
            return "👥 Recruit system not available.", None

    # ── dismiss ────────────────────────────────────────────────────────
    if kind == "dismiss":
        try:
            from canon_engine.systems.companions import dismiss
            result = dismiss(state, args.get("npc", ""))
            return result.get("narration", ""), None
        except Exception:
            return "👥 Dismiss system not available.", None

    # ── companion ──────────────────────────────────────────────────────
    if kind == "companion":
        try:
            from canon_engine.systems.companions import handle_companion_command
            result = handle_companion_command(state, {"action": args.get("npc", "list")})
            return result.get("narration", ""), None
        except Exception:
            return "👥 Companion system not available.", None

    # ── order ──────────────────────────────────────────────────────────
    if kind == "order":
        companion = args.get("companion", "")
        action = args.get("action", "")
        return f"📋 Ordered {companion} to: {action}", None

    # ── lockpick / gamble ──────────────────────────────────────────────
    if kind in ("lockpick", "gamble"):
        return f"🎮 {kind.title()} minigame — feature coming soon!", None

    # ── choices ────────────────────────────────────────────────────────
    if kind == "choices":
        return "📖 Narrative choices are presented by the narrator during story moments.", None

    # ── collide ────────────────────────────────────────────────────────
    if kind == "collide":
        genre1 = args.get("genre1", "")
        genre2 = args.get("genre2", "")
        return f"⚔ Genre collision: {genre1} × {genre2} — blending worlds!", None

    # ── summary ────────────────────────────────────────────────────────
    if kind == "summary":
        world_log = state.get("world_log", [])
        if not world_log:
            return "📖 No story yet. Start an adventure first!", None
        recent = world_log[-10:]
        lines = ["📖 **Previously on Canon Engine...**\n"]
        for entry in recent:
            text = entry.get("text", entry.get("narration", str(entry)))[:150] if isinstance(entry, dict) else str(entry)[:150]
            if text:
                lines.append(f"• {text}")
        return "\n".join(lines), None

    # ── encounter ──────────────────────────────────────────────────────
    if kind == "encounter":
        return _handle_encounter(state, rng), None

    # ── start_character ────────────────────────────────────────────────
    if kind == "start_character":
        # If character was provided at the top level, it's already handled
        return "Character created. Your adventure begins!", None

    # ── soul ───────────────────────────────────────────────────────────
    if kind == "soul":
        try:
            from canon_engine.core.underworld import soul_sheet
            return soul_sheet(state), None
        except Exception:
            return "👻 Underworld system not available.", None

    # ── admin / retcon ─────────────────────────────────────────────────
    if kind in ("admin", "retcon"):
        return f"🔧 Admin command received: {args}", None

    # ── unknown ────────────────────────────────────────────────────────
    return f"❓ Unknown command '/{kind}'. Type /help for available commands.", None


# ═══════════════════════════════════════════════════════════════════════════════
# ENCOUNTER HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def _handle_encounter(state: dict, rng: _random.Random) -> str:
    """Start a random encounter."""
    try:
        from canon_engine.core.combat import start_combat
        from canon_engine.core.enemy_ai import ENEMY_TYPES

        enemy_names = list(ENEMY_TYPES.keys())
        if not enemy_names:
            return "⚠ No enemies defined."

        count = rng.randint(1, 3)
        chosen = [rng.choice(enemy_names) for _ in range(count)]
        result = start_combat(state, {"enemies": chosen}, rng)

        names = ", ".join(result.get("enemies", chosen))
        return (
            f"⚔ **Encounter!**\n\n"
            f"You are ambushed by: {names}!\n\n"
            f"Use /attack to strike, /block to defend, or /flee to run!"
        )
    except Exception as exc:
        return f"⚠ Encounter failed: {exc}"


# ═══════════════════════════════════════════════════════════════════════════════
# HELP HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

def _handle_help_general() -> str:
    """General help text."""
    return (
        "**Canon Engine — Command Reference**\n\n"
        "**Core:** /say, /do, /think, /look\n"
        "**Combat:** /attack, /fight, /flee, /block, /item, /turn\n"
        "**Inventory:** /inv, /use, /equip, /inspect, /drop, /combine, /give\n"
        "**Character:** /stats, /addstat, /levelup, /skills, /unlock\n"
        "**World:** /lore, /map, /travel\n"
        "**NPCs:** /npcs, /npc, /talk, /gift, /threaten\n"
        "**Economy:** /shop, /buy, /sell, /barter, /scavenge, /rent\n"
        "**Factions:** /factions\n"
        "**Quests:** /quests, /quest, /accept, /abandon, /turnin\n"
        "**Stealth:** /scout, /stealth\n"
        "**Terrain:** /cover, /climb\n"
        "**Crafting:** /craft\n"
        "**Companions:** /recruit, /dismiss, /companion, /order\n"
        "**Recovery:** /nap, /sleep\n"
        "**Soul:** /soul\n"
        "**Story:** /choices, /collide, /summary\n"
        "**System:** /save, /load, /quicksave, /help, /menu, /quit\n\n"
        "Type `/help <topic>` for details on a specific topic."
    )


def _handle_help_topic(topic: str) -> str:
    """Help for a specific topic."""
    _TOPICS = {
        "combat": "Combat: /attack <target>, /block, /item <name>, /flee, /turn, /look enemies",
        "inventory": "Inventory: /inv, /use <item>, /equip <item>, /inspect <item>, /drop <item>",
        "character": "Character: /stats, /addstat <stat>, /levelup, /skills, /unlock <id>",
        "npcs": "NPCs: /npcs, /npc <id>, /talk, /gift <item> to <npc>, /threaten <npc>",
        "quests": "Quests: /quests, /quest <id>, /accept <id>, /abandon <id>, /turnin <id>",
        "economy": "Economy: /shop, /buy <item>, /sell <item>, /barter, /scavenge, /rent",
        "stealth": "Stealth: /scout, /stealth",
        "crafting": "Crafting: /craft list, /craft <recipe_id>",
    }
    return _TOPICS.get(topic.lower(), f"No help topic found for '{topic}'.")


# ═══════════════════════════════════════════════════════════════════════════════
# LAYOUT PAYLOAD BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_layout_payload(
    state: dict,
    narration: str = "",
    combat_active: bool = False,
) -> dict:
    """
    Build the full HUD layout payload from game state.

    Returns a JSON-serializable dict with all UI panels.
    """
    player = state.get("player", state)
    stats = player.get("stats", {})
    world = state.get("world", {})
    combat = state.get("combat", {})

    # Player info
    player_info = {
        "name": player.get("name", "Adventurer"),
        "hp": player.get("hp", 0),
        "hp_max": player.get("max_hp", player.get("hp", 0)),
        "mp": player.get("mp", 0),
        "mp_max": player.get("max_mp", player.get("mp", 0)),
        "stm": player.get("stm", player.get("stamina", 0)),
        "stm_max": player.get("max_stm", player.get("max_stamina", 0)),
        "xp": player.get("xp", 0),
        "xp_to_next": player.get("xp_to_next", player.get("xp_next", 100)),
        "level": player.get("level", 1),
        "stats": stats,
        "gold": player.get("gold", 0),
    }

    # Equipment
    equipment = state.get("equipment", {})

    # Inventory rows
    from canon_engine.core.inventory import format_inventory_rows
    try:
        inventory_rows = format_inventory_rows(state)
    except Exception:
        inventory_rows = []

    # Companions
    companions = state.get("companions", [])

    # Combat info
    combat_info = {}
    if combat_active or combat.get("active"):
        enemies = combat.get("enemies", [])
        combat_info = {
            "active": True,
            "round": combat.get("round", 0),
            "enemies": [
                {
                    "name": e.get("display_name", e.get("type", "enemy")),
                    "hp": e.get("hp", 0),
                    "max_hp": e.get("max_hp", 0),
                    "alive": e.get("alive", True),
                }
                for e in enemies
            ],
            "player_moves": combat.get("player_moves_remaining", 0),
        }

    # Suggested actions (from narrator result or defaults)
    suggested = state.get("_suggested_actions", [
        "/look", "/do examine surroundings", "/say hello", "/inv",
    ])

    # Skills
    skills_info = {
        "unlocked": state.get("unlocked_skills", player.get("skills", [])),
        "points": state.get("skill_points", player.get("skill_points", 0)),
    }

    # Saga
    saga = state.get("saga", {})

    # Codex (lore entries)
    codex = state.get("lore_entries", [])

    # Quests
    quests_data = state.get("quests", {})
    if isinstance(quests_data, dict):
        quest_list = quests_data.get("active", [])
    elif isinstance(quests_data, list):
        quest_list = quests_data
    else:
        quest_list = []

    # World info
    minutes = world.get("minutes_total", 0)
    hour = (minutes // 60) % 24
    minute_of_hour = minutes % 60
    day = minutes // 1440
    time_str = f"{hour:02d}:{minute_of_hour:02d} (Day {day})"

    world_info = {
        "clock": time_str,
        "weather": world.get("weather", "clear"),
        "sky": _sky_from_time(hour),
        "location": world.get("location_name", world.get("location_id", "Unknown")),
    }

    return {
        "player": player_info,
        "equipment": equipment,
        "inventory_rows": inventory_rows,
        "companions": companions,
        "combat": combat_info,
        "suggested_actions": suggested,
        "tutorial": state.get("tutorial", {}),
        "skills": skills_info,
        "saga": saga,
        "codex": codex,
        "quests": quest_list,
        "world": world_info,
        "dev_mode": state.get("dev_mode", False),
        "turn": state.get("turn", 0),
    }


def _sky_from_time(hour: int) -> str:
    """Return sky description from hour of day."""
    if 5 <= hour < 8:
        return "dawn"
    if 8 <= hour < 12:
        return "morning"
    if 12 <= hour < 14:
        return "noon"
    if 14 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 21:
        return "dusk"
    if 21 <= hour or hour < 5:
        return "night"
    return "day"


# ── Command application (legacy interface used by existing server.py) ────────

def _apply_parsed(state: Dict[str, Any], parsed: Dict[str, Any], *, config: Config | None = None) -> Dict[str, Any]:
    """Apply a parsed command to *state* and return the result payload.

    Parameters
    ----------
    state : dict
        The live game state (mutated in-place).
    parsed : dict
        The parsed command dict from ``core.command_parser.parse_command``.
    config : Config, optional
        Runtime config for model, verbosity, etc.

    Returns
    -------
    dict
        Keys: ``narration`` (str), ``events`` (list), ``state_delta`` (dict),
        ``layout`` (dict or None).
    """
    kind = parsed.get("kind", "unknown")
    result: Dict[str, Any] = {
        "narration": "",
        "events": [],
        "state_delta": {},
        "layout": None,
    }

    # ── Meta / UI commands (no engine call needed) ───────────────────────
    if kind == "help":
        result["narration"] = _handle_help(parsed, state)
        return result

    if kind == "menu":
        result["narration"] = "__QUIT__"
        return result

    if kind == "back":
        result["narration"] = "Closing overlay."
        return result

    if kind == "save":
        slot = parsed.get("slot") or ""
        # During combat, /save <ability> is a saving throw
        combat_state = state.get("combat", {})
        in_combat_now = bool(combat_state.get("active", False))
        _save_abilities = {"STR", "DEX", "CON", "INT", "WIS", "CHA"}
        if in_combat_now and slot.upper() in _save_abilities:
            from canon_engine.systems.combat import resolve_saving_throw
            save_parsed = {"kind": "saving_throw", "ability": slot.upper()}
            save_result = resolve_saving_throw(state, save_parsed)
            result["narration"] = save_result.get("narration", "")
            return result
        slot = slot or "quicksave"
        try:
            path = state_manager.save_state(state, slot)
            result["narration"] = f"💾 Game saved to slot '{slot}'."
        except Exception as exc:
            result["narration"] = f"❌ Save failed: {exc}"
        return result

    if kind == "load":
        slot = parsed.get("slot") or "quicksave"
        try:
            loaded = state_manager.load_state(slot)
            state.clear()
            state.update(loaded)
            result["narration"] = f"📂 Loaded save '{slot}'."
            result["state_delta"] = {"full_reload": True}
        except Exception as exc:
            result["narration"] = f"❌ Load failed: {exc}"
        return result

    if kind == "quicksave":
        try:
            path = state_manager.save_state(state, "quicksave")
            result["narration"] = "💾 Quicksave complete."
        except Exception as exc:
            result["narration"] = f"❌ Quicksave failed: {exc}"
        return result

    if kind == "dump":
        import json
        result["narration"] = "```json\n" + json.dumps(state, indent=2, default=str)[:3000] + "\n```"
        return result

    if kind == "verbose":
        level = parsed.get("level", 2)
        state.setdefault("settings", {})["verbosity"] = level
        result["narration"] = f"Narration verbosity set to {level}."
        return result

    if kind == "model":
        name = parsed.get("name", "")
        state.setdefault("settings", {})["llm_model"] = name
        result["narration"] = f"AI model switched to '{name}'."
        return result

    if kind == "lang":
        style = parsed.get("style", "default")
        state.setdefault("settings", {})["lang_style"] = style
        result["narration"] = f"Language style set to '{style}'."
        return result

    if kind == "godmode":
        player = state.get("player", {})
        for stat in ("STR", "DEX", "INT", "CHA", "CON", "LCK"):
            player.setdefault("stats", {})[stat] = 99
        player["hp"] = player.get("max_hp", 9999)
        player["mp"] = player.get("max_mp", 9999)
        result["narration"] = "⚡ GODMODE: All stats set to 99. HP/MP full."
        return result

    if kind == "tutorial":
        action = parsed.get("action", "open")
        result["narration"] = f"Tutorial: {action}"
        return result

    if kind == "error":
        result["narration"] = f"⚠ {parsed.get('error', 'Unknown error.')}"
        return result

    # ── Character creation ─────────────────────────────────────────────────
    if kind == "start_character":
        result["narration"] = _handle_start_character(state, parsed)
        return result

    # ── Random encounter ──────────────────────────────────────────────────
    if kind == "encounter":
        result["narration"] = _handle_encounter_legacy(state)
        return result

    # ── Display commands (formatted output, no AI call) ──────────────────
    if kind == "stats":
        player = state.get("player", {})
        stats = player.get("stats", {})
        name = player.get("name", "Adventurer")
        level = player.get("level", 1)
        hp = player.get("hp", 0)
        max_hp = player.get("max_hp", 0)
        xp = player.get("xp", 0)
        xp_needed = player.get("xp_next", 100)
        lines = [
            f"**{name}** — Level {level}",
            f"HP: {hp}/{max_hp}",
            f"XP: {xp}/{xp_needed}",
            "",
            "**Stats:**",
        ]
        for stat in ("STR", "DEX", "INT", "CHA", "CON", "LCK"):
            val = stats.get(stat, 10)
            mod = (val - 10) // 2
            sign = "+" if mod >= 0 else ""
            lines.append(f"  {stat}: {val} ({sign}{mod})")
        result["narration"] = "\n".join(lines)
        return result

    if kind == "inv":
        items = state.get("player", {}).get("inventory", [])
        if not items:
            items = state.get("inventory", [])
        if not items:
            result["narration"] = "🎒 Your inventory is empty."
            return result
        lines = ["**Inventory:**"]
        for i, item in enumerate(items):
            name = item.get("name", "Unknown") if isinstance(item, dict) else str(item)
            rarity = item.get("rarity", "Common") if isinstance(item, dict) else "Common"
            qty = item.get("qty", item.get("quantity", 1)) if isinstance(item, dict) else 1
            qty_str = f" x{qty}" if qty > 1 else ""
            lines.append(f"  {i+1}. {name} [{rarity}]{qty_str}")
        result["narration"] = "\n".join(lines)
        return result

    if kind == "companions":
        comps = state.get("companions", [])
        if not comps:
            result["narration"] = "👥 You have no companions."
            return result
        lines = ["**Companions:**"]
        for c in comps:
            cname = c.get("name", "Unknown")
            loyalty = c.get("loyalty", 0)
            status = c.get("status", "active")
            lines.append(f"  • {cname} — Loyalty: {loyalty}, Status: {status}")
        result["narration"] = "\n".join(lines)
        return result

    if kind == "quests":
        quests = state.get("quests", [])
        if not quests:
            result["narration"] = "📜 No active quests."
            return result
        lines = ["**Active Quests:**"]
        if isinstance(quests, dict):
            for q in quests.get("active", []):
                qname = q.get("title", q.get("name", "Unknown"))
                lines.append(f"  • {qname}")
        elif isinstance(quests, list):
            for q in quests:
                qname = q.get("name", "Unknown")
                status = q.get("status", "active")
                lines.append(f"  • {qname} [{status}]")
        result["narration"] = "\n".join(lines)
        return result

    if kind == "skills":
        player = state.get("player", {})
        skills = player.get("skills", [])
        points = player.get("skill_points", 0)
        if not skills:
            result["narration"] = f"🎯 No skills unlocked. Skill points available: {points}"
            return result
        lines = [f"**Skills** (Points: {points}):"]
        for s in skills:
            sname = s.get("name", "Unknown") if isinstance(s, dict) else str(s)
            lines.append(f"  • {sname}")
        result["narration"] = "\n".join(lines)
        return result

    if kind == "factions":
        facs = state.get("factions", {})
        if not facs:
            result["narration"] = "🏴 No known factions."
            return result
        lines = ["**Factions:**"]
        for fid, fdata in facs.items():
            rep = fdata.get("reputation", 0) if isinstance(fdata, dict) else 0
            lines.append(f"  • {fid}: Reputation {rep}")
        result["narration"] = "\n".join(lines)
        return result

    if kind == "world":
        world = state.get("world", {})
        loc = world.get("location_id", "Unknown")
        weather = world.get("weather", "clear")
        minutes = world.get("minutes_total", 0)
        hour = (minutes // 60) % 24
        day = minutes // 1440
        result["narration"] = f"**World State:**\nLocation: {loc}\nWeather: {weather}\nTime: {hour}:00 (Day {day})"
        return result

    if kind == "map":
        world = state.get("world", {})
        locations = world.get("locations", {})
        current = world.get("location_id", "Unknown")
        if not locations:
            result["narration"] = f"📍 Current location: {current}\nNo map data available."
            return result
        lines = [f"**Map** (Current: {current}):"]
        for lid, ldata in locations.items():
            marker = " ← YOU" if lid == current else ""
            lines.append(f"  • {lid}{marker}")
        result["narration"] = "\n".join(lines)
        return result

    # ── Combat state (needed by handlers below) ──────────────────────
    combat = state.get("combat", {})
    in_combat = bool(combat.get("active", False))

    # ── Author's Note / Tone Control ──────────────────────────────────
    if kind == "author":
        note = parsed.get("text", "").strip()
        if note:
            state.setdefault("settings", {})["author_note"] = note
            result["narration"] = f"📝 Author's note set: \"{note}\"\nThis will guide the narrator's tone and style."
        else:
            current = state.get("settings", {}).get("author_note", "")
            if current:
                result["narration"] = f"📝 Current author's note: \"{current}\"\nUse /author <text> to change."
            else:
                result["narration"] = "📝 No author's note set.\nUse /author <text> to set tone/style guidance."
        return result

    # ── Session Summary ────────────────────────────────────────────────
    if kind == "summary":
        world_log = state.get("world_log", [])
        if not world_log:
            result["narration"] = "📖 No story yet. Start an adventure first!"
            return result
        recent = world_log[-10:]
        lines = ["📖 **Previously on Canon Engine...**\n"]
        for entry in recent:
            narr = (entry.get("narration", "")[:150] if isinstance(entry, dict) else str(entry)[:150])
            if narr:
                lines.append(f"• {narr}")
        result["narration"] = "\n".join(lines)
        return result

    # ── Choices command ────────────────────────────────────────────────
    if kind == "choices":
        result["narration"] = "Narrative choices are presented during story moments."
        return result

    # ── Consequences command ───────────────────────────────────────────
    if kind == "consequences":
        result["narration"] = "Consequences unfold as the story progresses."
        return result

    # ── Collide command ────────────────────────────────────────────────
    if kind == "collide":
        args = parsed.get("text", parsed.get("genre1", "")).strip().split()
        genre1 = args[0] if args else ""
        genre2 = args[1] if len(args) > 1 else ""
        result["narration"] = f"⚔ Genre collision: {genre1} × {genre2} — blending worlds!"
        return result

    # ── Encounter command ──────────────────────────────────────────────
    if kind == "encounter" or (kind == "fight" and not in_combat):
        encounter_result = _handle_encounter_legacy(state)
        result["narration"] = encounter_result
        return result

    # ── AI narration commands ────────────────────────────────────────
    if kind in ("say", "do", "look"):
        try:
            from canon_engine.core.narrator import narrate_and_apply as _naa
            if kind == "look":
                player_input = "/do Look around carefully. Describe the scene cinematically."
            else:
                player_input = parsed.get("text", parsed.get("words", parsed.get("raw", "")))

            narr_result = _naa(state, player_input, turn=state.get("turn", 0))
            narration = narr_result.get("narration", "")
            if narration:
                state.setdefault("world_log", []).append({"input": player_input, "narration": narration[:200]})
                result["narration"] = narration
                return result
        except Exception as e:
            if kind == "look":
                result["narration"] = f"You look around. The scene is hard to make out. ({e})"
                return result
            result["narration"] = f"[Narrator unavailable: {e}]\nYou said: {parsed.get('text', parsed.get('words', ''))}"
            return result

    # ── Engine-delegated commands ────────────────────────────────────────
    combat = state.get("combat", {})
    in_combat = bool(combat.get("active", False))

    combat_kinds = {"attack", "fight", "flee", "block", "dodge", "item", "order", "turn", "saving_throw"}
    if in_combat and kind not in combat_kinds and kind not in {"look", "inv", "stats", "companions", "help", "save", "back", "dodge", "turn", "saving_throw"}:
        result["narration"] = "⚔ You're in combat! Use /attack, /dodge, /flee, /turn, or /item."
        return result

    # ── D&D 5e combat commands (handled directly) ─────────────────────
    if kind == "fight" and in_combat:
        result["narration"] = "You're already in combat! Use /attack <target> to fight."
        return result

    # Encounter routing
    encounter = state.get("encounter", {})
    in_encounter = bool(encounter.get("active", False))
    encounter_kinds = {"talk", "shop", "buy", "sell", "barter", "gift", "threaten", "flee"}
    if in_encounter and kind not in encounter_kinds and kind not in {"look", "inv", "stats", "help", "save", "back"}:
        result["narration"] = "💬 You're in an encounter! Use /talk, /shop, /buy, /sell, or /flee."
        return result

    # Delegate to engine
    try:
        step_fn = _get_step_turn()
        engine_result = step_fn(state, parsed, config=config)
        if isinstance(engine_result, dict):
            result["narration"] = engine_result.get("narration", "")
            result["events"] = engine_result.get("events", [])
            result["state_delta"] = engine_result.get("state_delta", {})
            result["layout"] = engine_result.get("layout")
        else:
            result["narration"] = str(engine_result) if engine_result else ""
    except Exception as exc:
        logger.exception("Engine error for command %s", kind)
        try:
            narrate_fn = _get_narrate()
            result["narration"] = narrate_fn(state, parsed)
        except Exception:
            result["narration"] = f"❌ Engine error: {exc}"

    # Append to command log
    state.setdefault("command_log", []).append({
        "kind": kind,
        "raw": parsed,
    })
    # Prune command log
    from canon_engine.constants import COMMAND_LOG_LIMIT
    log = state["command_log"]
    if len(log) > COMMAND_LOG_LIMIT:
        state["command_log"] = log[-COMMAND_LOG_LIMIT:]

    return result


def _handle_help(parsed: Dict[str, Any], state: Dict[str, Any]) -> str:
    """Generate help text for the /help command."""
    topic = parsed.get("topic")
    if topic:
        return _handle_help_topic(topic)
    return _handle_help_general()


# ── Handler: start_character (legacy) ──────────────────────────────────────────

def _handle_start_character(state: Dict[str, Any], parsed: Dict[str, Any]) -> str:
    """Handle /start_character: rebuild state from parsed character data."""
    from canon_engine.core.character_session import build_character_session_state

    character = {}
    for key in ("name", "archetype", "race", "stats", "genre", "setting", "speech", "backstory"):
        if key in parsed:
            character[key] = parsed[key]

    if not character.get("name"):
        character["name"] = parsed.get("name", "Adventurer")

    fresh = build_character_session_state(character)
    state.clear()
    state.update(fresh)

    name = character.get("name", "Adventurer")
    archetype = character.get("archetype", "adventurer")
    location = state.get("location", "a crossroads")
    player = state.get("player", {})

    narration = (
        f"**{name}** the {archetype} enters the world.\n\n"
        f"📍 {location}  |  HP: {player.get('hp', 0)}/{player.get('max_hp', 0)}\n\n"
        f"Your adventure begins. Type `/help` for commands."
    )
    return narration


# ── Handler: encounter (legacy) ───────────────────────────────────────────────

def _handle_encounter_legacy(state: Dict[str, Any]) -> str:
    """Handle /encounter using the core combat module."""
    rng = _random.Random()
    return _handle_encounter(state, rng)


# ── GameSession class ────────────────────────────────────────────────────────

class GameSession:
    """Wraps a single game session: state, config, and the command loop.

    Parameters
    ----------
    state : dict
        The live game state dict.
    config : Config, optional
        Runtime configuration.
    slot : str
        The save slot name.
    """

    def __init__(
        self,
        state: Dict[str, Any],
        config: Config | None = None,
        slot: str = "default",
    ) -> None:
        self.state = state
        self.config = config or Config()
        self.slot = slot
        self._turn_count = 0
        self._running = True

    @property
    def is_running(self) -> bool:
        """Whether the session loop should continue."""
        return self._running

    def stop(self) -> None:
        """Signal the session to stop after the current turn."""
        self._running = False

    def handle_command(self, text: str) -> Dict[str, Any]:
        """Process a single player command and return the result.

        Parameters
        ----------
        text : str
            Raw player input (e.g. ``"/look sword"`` or ``"Hello!"``).

        Returns
        -------
        dict
            Keys: narration, events, state_delta, layout.
        """
        from canon_engine.core.command_parser import parse_command

        parsed = parse_command(text)
        result = _apply_parsed(self.state, parsed, config=self.config)

        self._turn_count += 1

        # Autosave check
        if self.config.autosave_enabled:
            interval = self.state.get("settings", {}).get("autosave_interval", 5)
            if self._turn_count % interval == 0:
                try:
                    state_manager.autosave(self.state)
                except Exception as exc:
                    logger.warning("Autosave failed: %s", exc)

        # Check for quit signal
        if result.get("narration") == "__QUIT__":
            result["narration"] = "Session ended. Farewell, adventurer."
            self._running = False

        return result

    def run(self) -> None:
        """Blocking TUI loop using Rich console."""
        from rich.console import Console
        from rich.prompt import Prompt

        console = Console()
        console.print(f"\n[bold yellow]═══ {ENGINE_NAME} ═══[/bold yellow]\n")

        # Show initial narration if state has a location
        location = self.state.get("world", {}).get("location_name", "an unknown place")
        console.print(f"[dim]You find yourself at {location}.[/dim]\n")

        while self._running:
            try:
                text = Prompt.ask("[bold green]>[/bold green]")
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Session interrupted.[/dim]")
                break

            if not text.strip():
                continue

            result = self.handle_command(text)
            narration = result.get("narration", "")

            if narration and narration != "__QUIT__":
                console.print()
                console.print(narration)
                console.print()

        # Autosave on exit
        if self.config.autosave_enabled:
            try:
                state_manager.autosave(self.state)
                console.print("[dim]Autosaved.[/dim]")
            except Exception:
                pass

        console.print("[dim]Goodbye.[/dim]")
