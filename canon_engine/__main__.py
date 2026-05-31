"""Canon Engine – AI-powered text-based infinite RPG.

Usage::

    python -m canon_engine [--slot SLOT] [--tutorial]
"""
from __future__ import annotations

import argparse
import logging
import sys

from canon_engine.config import config
from canon_engine.constants import ENGINE_NAME, ENGINE_VERSION
from canon_engine import state_manager


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Canon Engine CLI."""
    parser = argparse.ArgumentParser(
        prog=ENGINE_NAME.replace(" ", "_").lower(),
        description=f"{ENGINE_NAME} v{ENGINE_VERSION} – AI-powered text RPG",
    )
    parser.add_argument(
        "--slot", default="default", help="Save slot to load (default: 'default')."
    )
    parser.add_argument(
        "--tutorial", action="store_true", help="Start in tutorial sandbox mode."
    )
    parser.add_argument(
        "--new-game", action="store_true", help="Force a fresh game even if the slot exists."
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("canon_engine")

    logger.info("%s v%s starting (slot=%r, tutorial=%s)",
                ENGINE_NAME, ENGINE_VERSION, args.slot, args.tutorial)

    # Load or create state.
    try:
        state = state_manager.load_state(args.slot)
        logger.info("Loaded existing save %r.", args.slot)
    except FileNotFoundError:
        state = state_manager.new_state()
        logger.info("No save found – created fresh state.")
    except state_manager.SaveVersionError as exc:
        logger.error("Incompatible save: %s", exc)
        return 1

    if args.new_game:
        state = state_manager.new_state()
        logger.info("Forced new game.")

    # Placeholder: hand off to the game loop.
    logger.info("State keys: %s", list(state.keys()))
    logger.info("Game loop not yet implemented – exiting.")

    # Autosave on exit (unless tutorial).
    if config.autosave_enabled:
        path = state_manager.autosave(state, is_tutorial=args.tutorial)
        if path:
            logger.info("Autosaved to %s", path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
