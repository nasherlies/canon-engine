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
        "**System:** /save, /load, /quicksave, /help, /menu, /quit\n\n"
        "Type `/help <topic>` for details on a specific topic."
    )


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
