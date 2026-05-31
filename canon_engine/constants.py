"""Global constants for Canon Engine.

Central place for magic strings, default values, and game-tuning knobs that
are referenced across multiple modules.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Engine identity
# ---------------------------------------------------------------------------

ENGINE_NAME: str = "Canon Engine"
ENGINE_VERSION: str = "0.1.0"

# ---------------------------------------------------------------------------
# Gameplay defaults
# ---------------------------------------------------------------------------

#: Maximum number of companion NPCs that can travel with the player at once.
MAX_PARTY_SIZE: int = 4

#: How many recent command-log entries to keep in the state before pruning.
COMMAND_LOG_LIMIT: int = 500

#: How many world-log entries to keep before pruning.
WORLD_LOG_LIMIT: int = 1000

#: Maximum tokens the LLM may generate in a single narrative response.
MAX_NARRATIVE_TOKENS: int = 2048

# ---------------------------------------------------------------------------
# File / path defaults
# ---------------------------------------------------------------------------

SAVES_DIR: str = "saves"
DOCS_DIR: str = "docs"
TESTS_DIR: str = "tests"
