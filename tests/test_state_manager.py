"""Tests for canon_engine.state_manager – the foundation layer.

Run with::

    python -m pytest tests/test_state_manager.py -v
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from canon_engine import state_manager
from canon_engine.state_manager import (
    CANON_SAVE_VERSION,
    InvalidSlotName,
    SaveVersionError,
    autosave,
    get_autosave_path,
    load_state,
    new_state,
    save_state,
    validate_slot_name,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _patch_saves_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect the saves directory to a temp folder for every test."""
    saves = tmp_path / "saves"
    saves.mkdir()
    monkeypatch.setattr(state_manager, "_saves_dir", lambda: saves)
    # Also need to override the project root so _assert_save_file_path works.
    monkeypatch.setattr(state_manager, "_project_root", lambda: tmp_path)
    return saves


# ── Slot validation ──────────────────────────────────────────────────────

class TestValidateSlotName:
    """validate_slot_name() should accept good names and reject bad ones."""

    @pytest.mark.parametrize("raw, expected", [
        ("default", "default"),
        ("  My Save  ", "my_save"),
        ("slot_123", "slot_123"),
        ("UPPER", "upper"),
        ("has space", "has_space"),
    ])
    def test_accepts_valid_names(self, raw: str, expected: str) -> None:
        assert validate_slot_name(raw) == expected

    @pytest.mark.parametrize("bad", [
        "", "   ",                       # empty / whitespace-only
        "dot.name",                      # dots
        "path/traversal",                # slashes
        "../escape",                     # directory traversal
        "a" * 65,                        # too long
        "con",                           # Windows reserved
        "AUX",                           # Windows reserved (case)
    ])
    def test_rejects_invalid_names(self, bad: str) -> None:
        with pytest.raises(InvalidSlotName):
            validate_slot_name(bad)


# ── new_state ────────────────────────────────────────────────────────────

class TestNewState:
    """new_state() should produce a valid, version-stamped skeleton."""

    def test_has_expected_keys(self) -> None:
        state = new_state()
        for key in ("player", "world", "combat", "companions", "memory",
                     "quests", "npcs", "factions", "saga", "world_bible",
                     "command_log", "world_log"):
            assert key in state, f"Missing key: {key}"

    def test_save_version(self) -> None:
        assert new_state()["save_version"] == CANON_SAVE_VERSION


# ── save / load round-trip ───────────────────────────────────────────────

class TestSaveLoadRoundTrip:
    """save_state → load_state should round-trip perfectly."""

    def test_round_trip(self) -> None:
        state = new_state()
        state["player"]["name"] = "Artemis"
        state["player"]["hp"] = 42
        state["quests"].append({"id": "q1", "title": "Find the Amulet"})

        save_state(state, "test_slot")
        loaded = load_state("test_slot")

        assert loaded["player"]["name"] == "Artemis"
        assert loaded["player"]["hp"] == 42
        assert loaded["quests"][0]["title"] == "Find the Amulet"
        assert loaded["save_version"] == CANON_SAVE_VERSION

    def test_loaded_state_is_deep_copy(self) -> None:
        """Mutating the loaded state must not affect a subsequent load."""
        state = new_state()
        state["player"]["name"] = "Original"
        save_state(state, "copy_test")

        first = load_state("copy_test")
        first["player"]["name"] = "Mutated"

        second = load_state("copy_test")
        assert second["player"]["name"] == "Original"

    def test_slot_sanitised_on_write(self) -> None:
        """Saving to '  My Slot  ' should create 'my_slot.json'."""
        state = new_state()
        path = save_state(state, "  My Slot  ")
        assert path.name == "my_slot.json"

    def test_save_overwrites_existing(self) -> None:
        state = new_state()
        state["player"]["hp"] = 10
        save_state(state, "overwrite")

        state["player"]["hp"] = 99
        save_state(state, "overwrite")

        loaded = load_state("overwrite")
        assert loaded["player"]["hp"] == 99


# ── load failure modes ───────────────────────────────────────────────────

class TestLoadFailures:
    """load_state() should raise clear errors for bad inputs."""

    def test_missing_slot_raises_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_state("nonexistent_slot")

    def test_bad_json_raises_save_load_error(self, tmp_path: Path) -> None:
        bad_file = state_manager._saves_dir() / "corrupt.json"
        bad_file.write_text("NOT VALID JSON {{{", encoding="utf-8")
        with pytest.raises(state_manager.SaveLoadError):
            load_state("corrupt")

    def test_wrong_version_raises_save_version_error(self, tmp_path: Path) -> None:
        bad = state_manager._saves_dir() / "oldver.json"
        bad.write_text(
            json.dumps({"save_version": 999, "player": {}}),
            encoding="utf-8",
        )
        with pytest.raises(SaveVersionError):
            load_state("oldver")

    def test_non_dict_raises_save_load_error(self) -> None:
        bad = state_manager._saves_dir() / "list.json"
        bad.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        with pytest.raises(state_manager.SaveLoadError):
            load_state("list")


# ── Path-jail ────────────────────────────────────────────────────────────

class TestPathJail:
    """_assert_save_file_path must reject paths that escape the saves dir."""

    def test_normal_path_allowed(self, tmp_path: Path) -> None:
        safe = tmp_path / "saves" / "ok.json"
        # Should not raise.
        state_manager._assert_save_file_path(safe)

    def test_traversal_rejected(self, tmp_path: Path) -> None:
        evil = tmp_path / "saves" / ".." / ".." / "etc" / "passwd"
        with pytest.raises(ValueError, match="Path-jail"):
            state_manager._assert_save_file_path(evil)


# ── Autosave ─────────────────────────────────────────────────────────────

class TestAutosave:
    """autosave() helper behaviour."""

    def test_autosave_slot_name(self) -> None:
        assert get_autosave_path() == "autosave"

    def test_autosave_writes_file(self) -> None:
        state = new_state()
        path = autosave(state)
        assert path is not None
        assert path.exists()

    def test_autosave_skipped_in_tutorial(self) -> None:
        state = new_state()
        result = autosave(state, is_tutorial=True)
        assert result is None

    def test_autosave_round_trip(self) -> None:
        state = new_state()
        state["player"]["level"] = 7
        autosave(state)
        loaded = load_state(get_autosave_path())
        assert loaded["player"]["level"] == 7
