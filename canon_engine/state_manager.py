"""State manager – the single source of truth for all Canon Engine game state.

Every subsystem reads and writes game state through this module.  The state
is a plain Python dict serialised to JSON on disk.  All I/O is atomic (write
to a temp file, then ``os.replace``) so a crash mid-write can never produce a
torn save.

Public API
----------
- ``CANON_SAVE_VERSION``         – schema version baked into every save file.
- ``new_state()``                – return a fresh, empty state dict.
- ``load_state(slot)``           – read + validate a save file.
- ``save_state(state, slot)``    – sanitise, deep-copy, write atomically.
- ``get_autosave_path()``        – canonical autosave slot name.
- ``validate_slot_name(slot)``   – sanitise a user-supplied slot string.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Bumped when the save-file schema changes.  Old saves are migrated (or
#: rejected) based on this value.
CANON_SAVE_VERSION: int = 1

#: Root directory that contains all save files.  Relative to the project root.
_SAVES_DIR_NAME: str = "saves"

#: Maximum length of a sanitised slot name (excluding extension).
_SLOT_MAX_LEN: int = 64

#: Characters allowed in a slot name (after lowercasing).
_SLOT_RE: re.Pattern[str] = re.compile(r"^[a-z0-9_]+$")

#: Windows reserved file names (case-insensitive).  Rejected even on Linux to
#: keep saves portable across platforms.
_WINDOWS_RESERVED: frozenset[str] = frozenset({
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
})

# Keys expected at the top level of a valid state dict.
_EXPECTED_STATE_KEYS: frozenset[str] = frozenset({
    "player", "world", "combat", "companions", "memory",
    "quests", "npcs", "factions", "saga", "world_bible",
    "command_log", "world_log",
})


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _project_root() -> Path:
    """Return the canonical project root (parent of ``canon_engine/``)."""
    # Walk up from this file until we find the directory that contains
    # ``canon_engine`` *and* ``saves`` (or the top-level package marker).
    here = Path(__file__).resolve().parent
    candidate = here.parent  # one level above canon_engine/
    if (candidate / "canon_engine").is_dir():
        return candidate
    # Fallback: two levels up (covers editable installs, tests, etc.)
    return here.parent.parent


def _saves_dir() -> Path:
    """Return (and lazily create) the saves directory."""
    d = _project_root() / _SAVES_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _assert_save_file_path(path: Path) -> None:
    """**Path-jail**: ensure *path* resolves inside the saves directory.

    Raises
    ------
    ValueError
        If the resolved path escapes the saves directory (e.g. via ``..``).
    """
    saves = _saves_dir().resolve()
    resolved = path.resolve()
    if not str(resolved).startswith(str(saves) + os.sep) and resolved != saves:
        raise ValueError(
            f"Path-jail violation: {path!r} resolves outside {saves!r}"
        )


# ---------------------------------------------------------------------------
# Slot-name sanitisation
# ---------------------------------------------------------------------------

class InvalidSlotName(ValueError):
    """Raised when a slot name fails sanitisation checks."""


def validate_slot_name(slot: str) -> str:
    """Validate and normalise a save-slot name.

    Rules
    -----
    1. Stripped of leading/trailing whitespace.
    2. Lowercased.
    3. Only ``[a-z0-9_]`` allowed after step 2.
    4. Must be non-empty and at most :pydata:`_SLOT_MAX_LEN` characters.
    5. Must not be a Windows reserved name (``con``, ``aux``, ``nul``, …).

    Returns
    -------
    str
        The sanitised slot name.

    Raises
    ------
    InvalidSlotName
        If any rule is violated.
    """
    cleaned = slot.strip().lower().replace(" ", "_")

    if not cleaned:
        raise InvalidSlotName("Slot name must not be empty.")

    if len(cleaned) > _SLOT_MAX_LEN:
        raise InvalidSlotName(
            f"Slot name too long ({len(cleaned)} > {_SLOT_MAX_LEN})."
        )

    if not _SLOT_RE.match(cleaned):
        raise InvalidSlotName(
            f"Slot name contains disallowed characters: {slot!r}. "
            f"Only lowercase letters, digits, and underscores are permitted."
        )

    if cleaned in _WINDOWS_RESERVED:
        raise InvalidSlotName(
            f"Slot name {cleaned!r} is a Windows reserved filename."
        )

    return cleaned


# ---------------------------------------------------------------------------
# State construction
# ---------------------------------------------------------------------------

def new_state() -> Dict[str, Any]:
    """Return a fresh, canonical state dict with all expected keys initialised.

    Every key listed in ``_EXPECTED_STATE_KEYS`` is present so that
    downstream code can always do a safe ``.get()`` or direct access without
    ``KeyError`` guards.
    """
    return {
        "save_version": CANON_SAVE_VERSION,
        "player": {},
        "world": {},
        "combat": {},
        "companions": [],
        "memory": {"summary": "", "last_summary_turn": 0},
        "quests": [],
        "npcs": {},
        "factions": {},
        "saga": {"phase": 0, "flags": []},
        "world_bible": {},
        "world_flags": {},
        "lore_cards": [],
        "equipment": {},
        "inventory": [],
        "turn": 0,
        "tutorial": {"active": False},
        "honor_score": 0,
        "chaos_score": 0,
        "command_log": [],
        "world_log": [],
    }


# ---------------------------------------------------------------------------
# Persistence – load
# ---------------------------------------------------------------------------

class SaveLoadError(Exception):
    """Base exception for save/load failures."""


class SaveVersionError(SaveLoadError):
    """The save file's version is incompatible with this engine version."""


def load_state(slot: str) -> Dict[str, Any]:
    """Load a game state dict from *slot*.

    Parameters
    ----------
    slot : str
        The save-slot name (will be sanitised).

    Returns
    -------
    dict
        A deep copy of the on-disk state so callers can mutate freely
        without affecting the loaded snapshot.

    Raises
    ------
    InvalidSlotName
        If the slot name is invalid.
    FileNotFoundError
        If the save file does not exist.
    SaveVersionError
        If ``save_version`` in the file does not match ``CANON_SAVE_VERSION``.
    SaveLoadError
        For other I/O or parse errors.
    """
    slot = validate_slot_name(slot)
    path = _saves_dir() / f"{slot}.json"
    _assert_save_file_path(path)

    if not path.is_file():
        raise FileNotFoundError(f"No save file for slot {slot!r} ({path}).")

    try:
        raw = path.read_text(encoding="utf-8")
        data: Dict[str, Any] = json.loads(raw)
    except (json.JSONDecodeError, OSError) as exc:
        raise SaveLoadError(f"Failed to read save {slot!r}: {exc}") from exc

    if not isinstance(data, dict):
        raise SaveLoadError(
            f"Save {slot!r} is not a JSON object (got {type(data).__name__})."
        )

    version = data.get("save_version")
    if version != CANON_SAVE_VERSION:
        raise SaveVersionError(
            f"Save {slot!r} has version {version!r}; "
            f"expected {CANON_SAVE_VERSION}."
        )

    # Return a deep copy so callers cannot accidentally mutate the in-memory
    # snapshot that subsequent loads would re-read from cache (if caching is
    # ever added).
    merged = new_state()
    merged.update(data)
    # Fix legacy shapes: memory must be dict, saga must be dict
    if isinstance(merged.get("memory"), list):
        merged["memory"] = {"summary": "", "last_summary_turn": 0}
    if isinstance(merged.get("saga"), list):
        merged["saga"] = {"phase": 0, "flags": []}
    return copy.deepcopy(merged)


# ---------------------------------------------------------------------------
# Persistence – save
# ---------------------------------------------------------------------------

def save_state(state: Dict[str, Any], slot: str) -> Path:
    """Persist *state* to *slot* using an atomic write.

    Steps
    -----
    1. Validate the slot name.
    2. Deep-copy *state* to avoid mutating the caller's reference.
    3. Stamp ``save_version``.
    4. Write JSON to a temporary file **in the same directory** (so
       ``os.replace`` is guaranteed atomic on the same filesystem).
    5. ``os.replace`` the temp file over the final path.

    Parameters
    ----------
    state : dict
        The full game-state dict.
    slot : str
        The save-slot name (will be sanitised).

    Returns
    -------
    pathlib.Path
        The resolved path of the written save file.

    Raises
    ------
    InvalidSlotName
        If the slot name is invalid.
    SaveLoadError
        For serialisation or I/O errors.
    """
    slot = validate_slot_name(slot)
    saves = _saves_dir()
    final_path = saves / f"{slot}.json"
    _assert_save_file_path(final_path)

    # Deep-copy to decouple from the caller's live state.
    snapshot = copy.deepcopy(state)
    snapshot["save_version"] = CANON_SAVE_VERSION

    try:
        payload = json.dumps(snapshot, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as exc:
        raise SaveLoadError(f"Cannot serialise state: {exc}") from exc

    # Atomic write: temp file → os.replace.
    tmp_fd: Optional[int] = None
    tmp_path: Optional[str] = None
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(
            suffix=".tmp",
            prefix=f".canon_save_{slot}_",
            dir=str(saves),
        )
        with os.fdopen(tmp_fd, mode="w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        tmp_fd = None  # fdopen took ownership

        os.replace(tmp_path, str(final_path))
        logger.info("Saved slot %r → %s", slot, final_path)
    except OSError as exc:
        raise SaveLoadError(f"Atomic write failed for slot {slot!r}: {exc}") from exc
    finally:
        # Clean up the temp file if something went wrong before os.replace.
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        if tmp_path is not None and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return final_path


# ---------------------------------------------------------------------------
# Autosave helpers
# ---------------------------------------------------------------------------

#: Canonical slot name for autosaves.
_AUTOSAVE_SLOT: str = "autosave"


def get_autosave_path() -> str:
    """Return the canonical autosave slot name.

    Usage::

        save_state(state, get_autosave_path())
    """
    return _AUTOSAVE_SLOT


def autosave(state: Dict[str, Any], *, is_tutorial: bool = False) -> Optional[Path]:
    """Convenience wrapper: save to the autosave slot unless in tutorial mode.

    Parameters
    ----------
    state : dict
        The current game state.
    is_tutorial : bool
        If ``True`` the autosave is **skipped** (tutorial sandbox is ephemeral).

    Returns
    -------
    pathlib.Path or None
        The save-file path, or ``None`` if the autosave was skipped.
    """
    if is_tutorial:
        logger.debug("Autosave skipped (tutorial sandbox).")
        return None
    return save_state(state, _AUTOSAVE_SLOT)
