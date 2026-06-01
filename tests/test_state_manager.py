"""Tests for canon_engine.core.state_manager."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from canon_engine.core.state_manager import (
    SaveValidationError,
    _merge_legacy_save_shape,
    load_game,
    save_game,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def default_state() -> dict:
    """Return a minimal valid state dict."""
    return {
        "save_version": 1,
        "player": {"name": "TestHero", "hp": 80, "hp_max": 100, "level": 3},
        "inventory": [{"name": "Sword"}],
        "equipment": {"weapon": "Iron Sword"},
        "companions": [],
        "world": {"location": "Forest"},
        "turn": 5,
    }


@pytest.fixture
def save_path(tmp_path: Path) -> Path:
    return tmp_path / "save.json"


# ── Round-trip save / load ────────────────────────────────────────────────

class TestSaveLoadRoundTrip:
    def test_basic_round_trip(self, default_state: dict, save_path: Path) -> None:
        save_game(default_state, str(save_path))
        loaded = load_game(str(save_path))

        assert loaded["save_version"] == 1
        assert loaded["player"]["name"] == "TestHero"
        assert loaded["player"]["hp"] == 80
        assert loaded["inventory"] == [{"name": "Sword"}]
        assert loaded["turn"] == 5

    def test_deep_copy_isolation(self, default_state: dict, save_path: Path) -> None:
        """Mutating loaded state must not affect a subsequent load."""
        save_game(default_state, str(save_path))

        first = load_game(str(save_path))
        first["player"]["name"] = "Mutated"

        second = load_game(str(save_path))
        assert second["player"]["name"] == "TestHero"

    def test_atomic_write_no_tmp_leftover(self, default_state: dict, save_path: Path) -> None:
        save_game(default_state, str(save_path))
        tmp = save_path.with_suffix(".json.tmp")
        assert save_path.exists()
        assert not tmp.exists()


# ── load_game failure modes ───────────────────────────────────────────────

class TestLoadFailures:
    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_game(str(tmp_path / "nonexistent.json"))

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("NOT VALID JSON {{{", encoding="utf-8")
        with pytest.raises(SaveValidationError, match="Invalid JSON"):
            load_game(str(bad))

    def test_wrong_version_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "old.json"
        bad.write_text(json.dumps({"save_version": 99}), encoding="utf-8")
        with pytest.raises(SaveValidationError, match="Unsupported save_version"):
            load_game(str(bad))

    def test_missing_version_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "nover.json"
        bad.write_text(json.dumps({"player": {}}), encoding="utf-8")
        with pytest.raises(SaveValidationError, match="Unsupported save_version"):
            load_game(str(bad))

    def test_non_dict_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "list.json"
        bad.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        with pytest.raises(SaveValidationError, match="JSON object"):
            load_game(str(bad))


# ── Legacy merge ──────────────────────────────────────────────────────────

class TestLegacyMerge:
    def test_fills_missing_keys(self) -> None:
        minimal = {"save_version": 1, "player": {"name": "Old"}}
        merged = _merge_legacy_save_shape(minimal)

        assert merged["player"]["name"] == "Old"
        assert merged["player"]["hp"] == 100  # default filled
        assert merged["player"]["stats"]["STR"] == 10  # nested default
        assert merged["inventory"] == []
        assert merged["world"]["location"] == "Unknown"
        assert merged["turn"] == 0
        assert merged["honor_score"] == 0
        assert merged["equipment_legacy_migrated"] is False

    def test_preserves_existing_nested_values(self) -> None:
        state = {
            "save_version": 1,
            "player": {"name": "X", "hp": 42},
            "world": {"location": "Castle", "weather": "rain"},
        }
        merged = _merge_legacy_save_shape(state)

        assert merged["player"]["hp"] == 42
        assert merged["player"]["hp_max"] == 100
        assert merged["world"]["location"] == "Castle"
        assert merged["world"]["weather"] == "rain"
        assert merged["world"]["sheltered"] is False

    def test_load_game_applies_merge(self, tmp_path: Path) -> None:
        """A partial save file should get merged defaults on load."""
        partial = {"save_version": 1, "player": {"name": "Legacy"}}
        p = tmp_path / "partial.json"
        p.write_text(json.dumps(partial), encoding="utf-8")

        loaded = load_game(str(p))
        assert loaded["player"]["name"] == "Legacy"
        assert loaded["player"]["hp"] == 100
        assert loaded["saga"]["phase"] == 0
