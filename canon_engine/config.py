"""Runtime configuration for Canon Engine.

Loads settings from environment variables with sensible defaults.  No external
dependency required (stdlib only).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Immutable runtime configuration.

    Environment variables
    ---------------------
    CANON_LLM_PROVIDER : str
        LLM backend identifier (default ``"openai"``).
    CANON_LLM_MODEL : str
        Model name / identifier (default ``"gpt-4o"``).
    CANON_LLM_API_KEY : str
        API key for the LLM provider.
    CANON_PROJECT_ROOT : str
        Override for the project root directory.
    CANON_LOG_LEVEL : str
        Python logging level (default ``"INFO"``).
    CANON_AUTOSAVE : str
        ``"1"`` to enable autosave, ``"0"`` to disable (default enabled).
    """

    llm_provider: str = field(
        default_factory=lambda: os.getenv("CANON_LLM_PROVIDER", "openai")
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("CANON_LLM_MODEL", "gpt-4o")
    )
    llm_api_key: str = field(
        default_factory=lambda: os.getenv("CANON_LLM_API_KEY", "")
    )
    project_root: Path = field(
        default_factory=lambda: Path(
            os.getenv("CANON_PROJECT_ROOT", str(Path(__file__).resolve().parent.parent))
        )
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("CANON_LOG_LEVEL", "INFO").upper()
    )
    autosave_enabled: bool = field(
        default_factory=lambda: os.getenv("CANON_AUTOSAVE", "1") == "1"
    )


# Module-level singleton – importable as ``from canon_engine.config import config``.
config = Config()
