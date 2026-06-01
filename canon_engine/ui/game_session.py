"""Game session – the main interactive loop for Canon Engine.

This module owns the *single source of truth* for what players can do during
a session.  It takes parsed commands (from ``core.command_parser``), applies
them to the game state via ``_apply_parsed``, and returns narration + layout
data for the UI layer.

Public API
----------
* ``GameSession`` – wraps state, engine, and UI concerns.
* ``GameSession.run()`` – blocking TUI loop (Rich terminal).
* ``GameSession.handle_command(text)`` – single command turn (for API use).
"""

from __future__ import annotations

import logging
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


# ── Command application ──────────────────────────────────────────────────────

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
        slot = parsed.get("slot") or "quicksave"
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
        result["narration"] = _handle_encounter(state)
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
        from canon_engine.systems.character import xp_to_next
        xp_needed = xp_to_next(level)
        lines = [
            f"**{name}** — Level {level}",
            f"HP: {hp}/{max_hp}",
            f"XP: {xp}/{xp_needed}",
            "",
            "**Stats:**",
        ]
        for stat in ("STR", "DEX", "INT", "CHA", "CON", "LCK"):
            val = stats.get(stat, 10)
            from canon_engine.systems.character import score_to_modifier
            mod = score_to_modifier(val)
            sign = "+" if mod >= 0 else ""
            lines.append(f"  {stat}: {val} ({sign}{mod})")
        result["narration"] = "\n".join(lines)
        return result

    if kind == "inv":
        items = state.get("player", {}).get("inventory", [])
        if not items:
            result["narration"] = "🎒 Your inventory is empty."
            return result
        lines = ["**Inventory:**"]
        for i, item in enumerate(items):
            name = item.get("name", "Unknown") if isinstance(item, dict) else str(item)
            rarity = item.get("rarity", "Common") if isinstance(item, dict) else "Common"
            qty = item.get("quantity", 1) if isinstance(item, dict) else 1
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
                result["narration"] = "📝 No author's note set.\nUse /author <text> to set tone/style guidance.\nExample: /author Write in dark fantasy style, keep responses under 200 words."
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
        from canon_engine.systems.story_branch import handle_choices_command
        result["narration"] = handle_choices_command(state)
        return result

    # ── Consequences command ───────────────────────────────────────────
    if kind == "consequences":
        from canon_engine.systems.story_branch import handle_consequences_command
        result["narration"] = handle_consequences_command(state)
        return result

    # ── Collide command ────────────────────────────────────────────────
    if kind == "collide":
        from canon_engine.systems.genre_collision import get_collision, list_collisions, apply_collision, describe_collision
        args = parsed.get("text", "").strip().split()
        if not args or args[0] == "list":
            collisions = list_collisions()
            lines = ["⚔ **Genre Collisions Available:**\n"]
            for c in collisions:
                lines.append(f"• **{c['name']}** — {c['genres'][0]} × {c['genres'][1]}")
            lines.append("\nUse `/collide <genre1> <genre2>` to blend genres!")
            result["narration"] = "\n".join(lines)
        elif len(args) >= 2:
            col = get_collision(args[0], args[1])
            if col:
                state = apply_collision(state, col["id"])
                result["narration"] = col.get("opening_narration", f"Genre collision: {col['name']} activated!")
            else:
                result["narration"] = f"No collision template found for '{args[0]}' × '{args[1]}'.\nUse `/collide list` to see available collisions."
        else:
            result["narration"] = "Usage: `/collide <genre1> <genre2>` or `/collide list`"
        return result

    # ── Encounter command ──────────────────────────────────────────────
    if kind == "encounter" or (kind == "fight" and not in_combat):
        encounter_result = _handle_encounter(state)
        result["narration"] = encounter_result
        return result

        # ── AI narration commands ────────────────────────────────────────
    if kind in ("say", "do", "look"):
        from canon_engine.narrator import narrate as ai_narrate
        from canon_engine.openai_client import MissingAPIKeyError

        if kind == "look":
            player_input = "/look around carefully. Describe the scene cinematically."
        else:
            player_input = parsed.get("text", parsed.get("raw", ""))

        try:
            narr_resp = ai_narrate(state, player_input)
            narration = narr_resp.narration if hasattr(narr_resp, "narration") else str(narr_resp)
            if not narration or narration.strip() == "":
                raise ValueError("Empty narration")

            # Apply state updates if narrator provided them
            if hasattr(narr_resp, "state_updates") and narr_resp.state_updates:
                for k, v in narr_resp.state_updates.items():
                    if isinstance(v, dict) and isinstance(state.get(k), dict):
                        state[k].update(v)
                    else:
                        state[k] = v

            # Append to world log
            state.setdefault("world_log", []).append({"input": player_input, "narration": narration[:200]})
            result["narration"] = narration
            return result
        except (MissingAPIKeyError, Exception) as e:
            if kind == "look":
                from canon_engine.systems.world import describe_location
                result["narration"] = describe_location(state)
                return result
            result["narration"] = f"[Narrator unavailable: {e}]\nYou said: {player_input}"
            return result

    # ── Engine-delegated commands ────────────────────────────────────────
    # Combat routing
    combat = state.get("combat", {})
    in_combat = bool(combat.get("active", False))

    combat_kinds = {"attack", "fight", "flee", "block", "item", "order"}
    if in_combat and kind not in combat_kinds and kind not in {"look", "inv", "stats", "companions", "help", "save", "back"}:
        result["narration"] = "⚔ You're in combat! Use /attack, /block, /flee, or /item."
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
        # Fallback: try direct narration
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
        # Try loading from handbook
        import json
        from pathlib import Path
        topics_path = Path(__file__).resolve().parent.parent.parent / "content" / "handbook" / "topics.json"
        if topics_path.exists():
            topics = json.loads(topics_path.read_text(encoding="utf-8"))
            if isinstance(topics, dict) and topic in topics:
                t = topics[topic]
                return f"**{t.get('title', topic)}**\n\n{t.get('body', 'No content.')}"
        return f"No handbook entry found for '{topic}'."

    # General help
    return (
        "**Canon Engine — Command Reference**\n\n"
        "**Core:** /say, /do, /look, /move\n"
        "**Combat:** /attack, /fight, /flee, /block, /item, /order\n"
        "**Inventory:** /inv, /use, /equip, /inspect, /drop, /combine, /give\n"
        "**Character:** /stats, /companions, /skills, /unlock, /levelup, /addstat\n"
        "**World:** /lore, /world, /map, /travel\n"
        "**NPCs:** /talk, /shop, /buy, /sell, /barter, /scavenge, /rent\n"
        "**Factions:** /factions, /reputation\n"
        "**Quests:** /quests, /quest, /accept, /abandon, /turnin\n"
        "**Stealth:** /scout, /stealth, /detect, /disarm\n"
        "**Crafting:** /craft\n"
        "**Soul:** /soul, /remember, /anchor, /bribe, /ascend, /descend, /rebirth\n"
        "**Story:** /choices, /consequences, /author, /summary\n"
        "**Genre:** /collide\n"
        "**System:** /save, /load, /quicksave, /help, /menu, /quit\n\n"
        "Type `/help <topic>` for details on a specific topic."
    )


# ── Handler: start_character ──────────────────────────────────────────────────

def _handle_start_character(state: Dict[str, Any], parsed: Dict[str, Any]) -> str:
    """Handle /start_character: rebuild state from parsed character data.

    The ``parsed`` dict may contain character data injected by the API
    endpoint or by the command parser.  Fields: name, archetype, stats,
    speech_style, setting_primary, setting_secondary, starting_location,
    preset_id.
    """
    from canon_engine.systems.character import (
        create_character as _create_char,
        max_hp as _max_hp,
        score_to_modifier,
    )

    # If a preset_id is provided, load it
    preset_data: Dict[str, Any] = {}
    preset_id = parsed.get("preset_id")
    if preset_id:
        from pathlib import Path
        import json
        presets_path = Path(__file__).resolve().parent.parent.parent / "content" / "presets" / "characters.json"
        if presets_path.exists():
            try:
                all_presets = json.loads(presets_path.read_text(encoding="utf-8"))
                preset_data = all_presets.get(preset_id, {})
            except Exception:
                pass

    char_name = parsed.get("name") or preset_data.get("name", "Adventurer")
    archetype = parsed.get("archetype") or preset_data.get("archetype", "Adventurer")
    stats = parsed.get("stats") or preset_data.get("stats", {})
    speech_style = parsed.get("speech_style") or preset_data.get("speech_style", "default")
    starting_gear = preset_data.get("starting_gear", [])
    setting_primary = parsed.get("setting_primary", "medieval_fantasy")
    setting_secondary = parsed.get("setting_secondary")

    # Generate random stats if none provided
    if not stats:
        fresh = _create_char(char_name, klass=archetype)
        stats = fresh["stats"]

    for s in ("STR", "DEX", "INT", "CHA", "CON", "LCK"):
        stats.setdefault(s, 10)

    con = stats.get("CON", 10)
    hp = _max_hp(con)
    dex = stats.get("DEX", 10)

    inventory = [{"name": g, "rarity": "common", "qty": 1} for g in starting_gear]
    if not inventory:
        inventory = [{"name": "health_potion", "rarity": "common", "qty": 2}]

    # Starting location
    location = parsed.get("starting_location")
    if not location:
        _genres = {
            "medieval_fantasy": "The Crossroads Inn",
            "space_opera": "Starport Delta",
            "gothic_horror": "Ravenmoor Manor Gate",
            "western": "Dusty Gulch Train Station",
            "anime_dramatic": "Academy Courtyard",
        }
        location = _genres.get(setting_primary, "The Crossroads Inn")

    # Rebuild state
    new = state_manager.new_state()
    state.clear()
    state.update(new)

    state["player"] = {
        "name": char_name,
        "archetype": archetype,
        "level": 1,
        "xp": 0,
        "xp_next": 100,
        "stats": stats,
        "hp": hp,
        "max_hp": hp,
        "mp": stats.get("INT", 10) * 3,
        "max_mp": stats.get("INT", 10) * 3,
        "stamina": 80,
        "max_stamina": 80,
        "ac": 10 + score_to_modifier(dex),
        "proficiency_bonus": 2,
        "skill_points": 0,
        "skills": [],
        "conditions": [],
        "gold": 50,
        "inventory": inventory,
        "speech_style": speech_style,
    }
    state["world"] = {
        "setting_primary": setting_primary,
        "setting_secondary": setting_secondary,
        "location_id": location.lower().replace(" ", "_"),
        "location_name": location,
        "weather": "clear",
        "minutes_total": 480,
        "locations": {
            location.lower().replace(" ", "_"): {"name": location, "discovered": True}
        },
    }
    state["combat"] = {"active": False, "enemies": [], "active_enemy_index": 0, "round": 0, "turn": "player"}
    state["companions"] = []
    state["quests"] = []
    state["world_log"] = [f"{char_name} awakens at {location}."]

    narration = (
        f"**{char_name}** the {archetype} enters the world.\n\n"
        f"📍 {location}  |  HP: {hp}/{hp}  |  AC: {state['player']['ac']}\n\n"
    )
    if inventory:
        item_names = ", ".join(i["name"] for i in inventory)
        narration += f"🎒 Starting gear: {item_names}\n\n"
    narration += "Your adventure begins. Type `/help` for commands."
    return narration


# ── Handler: encounter ───────────────────────────────────────────────────────

def _handle_encounter(state: Dict[str, Any]) -> str:
    """Handle /encounter: load enemies.json, pick weighted random enemies,
    and start combat via combat.start_combat()."""
    import random as _random
    import json
    from pathlib import Path

    enemies_path = Path(__file__).resolve().parent.parent.parent / "content" / "enemies.json"
    if not enemies_path.exists():
        return "⚠ No enemies data found."

    try:
        enemies_data = json.loads(enemies_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"⚠ Failed to load enemies: {exc}"

    enemy_pool = enemies_data.get("enemies", [])
    if not enemy_pool:
        return "⚠ No enemies defined."

    # Filter out zero-weight enemies (e.g. tutorial dummy)
    eligible = [e for e in enemy_pool if e.get("encounter_weight", 0) > 0]
    if not eligible:
        eligible = enemy_pool

    weights = [e.get("encounter_weight", 1) for e in eligible]
    count = _random.randint(1, 3)

    try:
        from canon_engine.systems.combat import start_combat as _start_combat
    except ImportError:
        return "⚠ Combat system not available."

    chosen = []
    for _ in range(count):
        pick = _random.choices(eligible, weights=weights, k=1)[0]
        enemy_copy = {
            "name": pick["name"],
            "hp": pick["hp"],
            "max_hp": pick["max_hp"],
            "ac": pick["ac"],
            "attack_bonus": pick.get("str", 10) // 2 + 2,
            "damage_dice": "1d6",
            "xp_value": pick.get("xp_value", 10),
        }
        chosen.append(enemy_copy)

    _start_combat(state, chosen)

    enemy_names = ", ".join(e["name"] for e in chosen)
    narration = f"⚔ **Encounter!**\n\nYou are ambushed by: {enemy_names}!\n\n"
    for e in chosen:
        narration += f"• **{e['name']}** — HP: {e['hp']}/{e['max_hp']}, AC: {e['ac']}\n"
    narration += "\nUse `/attack` to strike, `/block` to defend, or `/flee` to run!"
    return narration


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
        from core.command_parser import parse_command

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
