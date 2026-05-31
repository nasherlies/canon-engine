# Canon Engine

**AI-powered text-based infinite RPG engine.**

## Quick Start

```bash
# Run from the project root:
python -m canon_engine --slot default

# Start a tutorial sandbox (no autosave):
python -m canon_engine --tutorial

# Force a fresh game:
python -m canon_engine --slot default --new-game
```

## Project Structure

```
canon-engine/
├── canon_engine/
│   ├── __init__.py          # Package marker + version
│   ├── __main__.py          # CLI entry point
│   ├── state_manager.py     # Foundation: load/save/autosave (atomic writes, path-jail)
│   ├── config.py            # Runtime config (env vars → dataclass)
│   ├── constants.py         # Global constants and tuning knobs
│   ├── systems/             # Game subsystems (combat, quests, NPCs, …)
│   ├── adapters/            # External service adapters (LLM, TTS, …)
│   └── ui/                  # Interface layer (Telegram, web, CLI)
├── saves/                   # Save files (managed by state_manager)
├── tests/                   # Pytest test suite
├── docs/                    # Documentation
└── pyproject.toml           # Project metadata + build config
```

## Core Architecture

The **state_manager** is the foundation of the entire engine:

- **One big dict.** All game state lives in a single Python dict with keys
  `player`, `world`, `combat`, `companions`, `memory`, `quests`, `npcs`,
  `factions`, `saga`, `world_bible`, `command_log`, `world_log`, etc.
- **Atomic saves.** Writes go to a temp file, then `os.replace` — a crash
  mid-write can never produce a torn save.
- **Path jail.** Save files must resolve directly under `saves/`; directory
  traversal (`..`) is blocked.
- **Slot sanitisation.** Lowercase, `[a-z0-9_]` only, length limit,
  Windows reserved names rejected.
- **Autosave.** Dirty turns in campaign mode auto-save; skipped in tutorial
  sandbox.

## Running Tests

```bash
python -m pytest tests/ -v
```
