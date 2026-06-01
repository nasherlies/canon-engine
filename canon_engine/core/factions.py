"""Canon Engine — Faction reputation system."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# ── Content loader ────────────────────────────────────────────────────────

_CONTENT_DIR = Path(os.environ.get(
    "CANON_CONTENT_DIR",
    Path(__file__).resolve().parents[2] / "content",
))


def _load_json(name: str) -> dict:
    p = _CONTENT_DIR / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, val))


# ── Tier definitions ──────────────────────────────────────────────────────

FACTION_TIERS: list[tuple[str, int, int]] = [
    ("hated",     -100, -50),
    ("hostile",    -50, -20),
    ("unfriendly", -20, -10),
    ("neutral",    -10,  10),
    ("friendly",    10,  30),
    ("allied",      30,  60),
    ("honored",     60, 100),
]

# Shop price modifier by tier (hostile = expensive, honored = cheap)
_SHOP_MODIFIERS: dict[str, float] = {
    "hated":     1.5,
    "hostile":   1.3,
    "unfriendly": 1.15,
    "neutral":   1.0,
    "friendly":  0.8,
    "allied":    0.7,
    "honored":   0.6,
}


# ── Core functions ────────────────────────────────────────────────────────

def ensure_factions(state: dict[str, Any]) -> dict[str, dict]:
    """Ensure state['world']['factions'] exists and return it."""
    w = state.setdefault("world", {})
    w.setdefault("factions", {})
    return w["factions"]


def get_faction(state: dict[str, Any], faction_id: str) -> dict | None:
    """Return faction state dict by id, or None."""
    return ensure_factions(state).get(faction_id)


def apply_reputation_delta(state: dict[str, Any], faction_id: str, delta: int) -> dict:
    """Update faction reputation by delta, clamp to ±100, update tier."""
    factions = ensure_factions(state)
    faction = factions.get(faction_id)
    if faction is None:
        # Initialize from content
        content = _load_json("factions.json")
        base = content.get(faction_id, {})
        faction = {
            "id": faction_id,
            "name": base.get("name", faction_id),
            "description": base.get("description", ""),
            "reputation": base.get("base_rep", 0),
            "tier": "neutral",
        }
        factions[faction_id] = faction

    old = faction.get("reputation", 0)
    new_rep = _clamp(old + delta, -100, 100)
    faction["reputation"] = new_rep
    faction["tier"] = get_faction_tier(state, faction_id)
    return faction


def get_faction_tier(state: dict[str, Any], faction_id: str) -> str:
    """Return tier name for current reputation value."""
    faction = get_faction(state, faction_id)
    if faction is None:
        return "neutral"
    rep = faction.get("reputation", 0)
    for tier_name, lo, hi in FACTION_TIERS:
        if lo <= rep <= hi:
            return tier_name
    # Edge cases
    if rep < -100:
        return "hated"
    return "honored"


def get_shop_modifier(state: dict[str, Any], faction_id: str) -> float:
    """Return price multiplier based on faction tier."""
    tier = get_faction_tier(state, faction_id)
    return _SHOP_MODIFIERS.get(tier, 1.0)


def format_faction_sheet(state: dict[str, Any]) -> str:
    """Format all faction standings."""
    factions = ensure_factions(state)
    if not factions:
        return "No faction data."

    lines = ["**Faction Standings:**"]
    for fid, fdata in factions.items():
        rep = fdata.get("reputation", 0)
        tier = fdata.get("tier", get_faction_tier(state, fid))
        tier_icon = {
            "hated": "💀", "hostile": "⚔️", "unfriendly": "👎",
            "neutral": "🤝", "friendly": "👍", "allied": "🛡️", "honored": "⭐"
        }.get(tier, "❓")
        lines.append(f"  {tier_icon} **{fdata.get('name', fid)}**: {rep} ({tier})")
    return "\n".join(lines)


def check_nemesis_encounter(state: dict[str, Any], faction_id: str) -> bool:
    """If faction is hated, nemesis may appear (50% chance)."""
    tier = get_faction_tier(state, faction_id)
    if tier != "hated":
        return False
    # In a real game this would use rng; here we just indicate it's possible
    return True
