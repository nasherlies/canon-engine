"""Damage type registry."""

from __future__ import annotations

DAMAGE_TYPES: list[str] = [
    "physical",
    "fire",
    "ice",
    "lightning",
    "poison",
    "holy",
    "dark",
    "arcane",
]

# Display labels
_LABELS: dict[str, str] = {
    "physical":  "⚔ Physical",
    "fire":      "🔥 Fire",
    "ice":       "❄ Ice",
    "lightning": "⚡ Lightning",
    "poison":    "☠ Poison",
    "holy":      "✨ Holy",
    "dark":      "🌑 Dark",
    "arcane":    "🔮 Arcane",
}


def normalize_damage_type(raw: str) -> str:
    """Case-insensitive match against DAMAGE_TYPES, default 'physical'."""
    lower = raw.strip().lower()
    if lower in DAMAGE_TYPES:
        return lower
    return "physical"


def get_element_label(dtype: str) -> str:
    """Return a display label for the damage type."""
    return _LABELS.get(dtype, f"? {dtype}")
