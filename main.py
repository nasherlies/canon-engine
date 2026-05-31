#!/usr/bin/env python3
"""Canon Engine — Main entry point.

Parses CLI arguments, loads config, shows the start screen or launches
the API server, and wires up state_manager, engine, and UI.

Usage::

    # Interactive terminal mode
    python main.py --slot my_game

    # Tutorial mode
    python main.py --tutorial

    # New game (ignore existing save)
    python main.py --new-game --slot fresh_start

    # Developer mode (auto-loads, extra logging)
    python main.py --dev

    # API server mode
    python main.py --serve
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on the path so imports work when running directly.
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _load_dotenv() -> None:
    """Load .env file if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        env_path = _PROJECT_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass


def main(argv: list[str] | None = None) -> int:
    """Canon Engine CLI entry point."""
    _load_dotenv()

    from canon_engine.config import Config
    from canon_engine.constants import ENGINE_NAME, ENGINE_VERSION
    from canon_engine import state_manager

    parser = argparse.ArgumentParser(
        prog="canon-engine",
        description=f"{ENGINE_NAME} v{ENGINE_VERSION} — AI-powered text-based infinite RPG",
    )
    parser.add_argument(
        "--slot", default="default",
        help="Save slot name to load (default: 'default').",
    )
    parser.add_argument(
        "--tutorial", action="store_true",
        help="Start in tutorial sandbox mode.",
    )
    parser.add_argument(
        "--new-game", action="store_true",
        help="Force a fresh game even if the save slot exists.",
    )
    parser.add_argument(
        "--dev", action="store_true",
        help="Developer mode: extra logging, skip confirmations.",
    )
    parser.add_argument(
        "--serve", action="store_true",
        help="Launch the FastAPI HTTP server instead of the terminal UI.",
    )
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="API server host (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port", type=int, default=8787,
        help="API server port (default: 8787).",
    )

    args = parser.parse_args(argv)

    # ── Logging ──────────────────────────────────────────────────────────
    log_level = "DEBUG" if args.dev else "INFO"
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("canon_engine")

    # ── Config ───────────────────────────────────────────────────────────
    config = Config()
    logger.info("%s v%s starting (slot=%r, tutorial=%s, dev=%s, serve=%s)",
                ENGINE_NAME, ENGINE_VERSION, args.slot, args.tutorial, args.dev, args.serve)

    # ── API server mode ──────────────────────────────────────────────────
    if args.serve:
        from canon_engine.api.server import run_server
        run_server(host=args.host, port=args.port)
        return 0

    # ── Load or create state ─────────────────────────────────────────────
    try:
        state = state_manager.load_state(args.slot)
        logger.info("Loaded existing save %r.", args.slot)
    except FileNotFoundError:
        state = state_manager.new_state()
        logger.info("No save found — created fresh state.")
    except state_manager.SaveVersionError as exc:
        logger.error("Incompatible save: %s", exc)
        return 1

    if args.new_game:
        state = state_manager.new_state()
        logger.info("Forced new game.")

    # ── Start screen ─────────────────────────────────────────────────────
    from canon_engine.ui.start_screen import run_start_screen

    settings: dict = state.get("settings", {})
    choice = run_start_screen(settings)
    state["settings"] = settings

    if choice == "close":
        logger.info("User chose CLOSE from start screen.")
        if config.autosave_enabled:
            state_manager.autosave(state, is_tutorial=args.tutorial)
        return 0

    # ── Setup (character, world, location) if new game ───────────────────
    if args.new_game or not state.get("player"):
        from canon_engine.ui.prompts import run_full_setup
        setup = run_full_setup()

        # Merge setup into state
        world_info = setup.get("world", {})
        char_info = setup.get("character", {})
        loc_info = setup.get("location", {})

        state["player"] = {
            "name": char_info.get("name", "Adventurer"),
            "stats": char_info.get("stats", {
                "STR": 13, "DEX": 12, "INT": 12,
                "CHA": 12, "CON": 12, "LCK": 9,
            }),
            "archetype": char_info.get("archetype", "knight"),
            "speech_style": char_info.get("speech_style", "default"),
            "backstory": char_info.get("backstory", ""),
            "hp": 100,
            "max_hp": 100,
            "mp": 50,
            "max_mp": 50,
            "stamina": 80,
            "max_stamina": 80,
            "level": 1,
            "xp": 0,
            "xp_next": 100,
            "gold": 50,
            "inventory": [],
            "skills": [],
        }

        state["world"] = {
            "genre": world_info.get("genre", "fantasy"),
            "world_name": world_info.get("name", "Unknown Realm"),
            "location_id": loc_info.get("id", loc_info.get("name", "tavern")),
            "location_name": loc_info.get("name", "The Rusty Tankard"),
            "description": loc_info.get("description", ""),
            "seed": world_info.get("seed", ""),
        }

        logger.info("Setup complete: %s the %s in %s",
                     state["player"]["name"],
                     state["player"]["archetype"],
                     state["world"]["location_name"])

    # ── Tutorial mode ────────────────────────────────────────────────────
    if args.tutorial:
        state.setdefault("settings", {})["tutorial"] = True
        logger.info("Tutorial mode enabled.")

    # ── Launch game session ──────────────────────────────────────────────
    from canon_engine.ui.game_session import GameSession

    session = GameSession(state=state, config=config, slot=args.slot)
    session.run()

    # ── Save on exit ─────────────────────────────────────────────────────
    if config.autosave_enabled:
        path = state_manager.autosave(state, is_tutorial=args.tutorial)
        if path:
            logger.info("Autosaved to %s", path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
