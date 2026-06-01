"""Canon Engine — NPC system: registry, relationships, and memory."""

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


# ── Helpers ───────────────────────────────────────────────────────────────

def _clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, val))


def _disposition_from_rel(rel: int) -> str:
    if rel >= 30:
        return "friendly"
    if rel <= -30:
        return "hostile"
    return "neutral"


# ── Core functions ────────────────────────────────────────────────────────

def ensure_npcs(state: dict[str, Any]) -> dict[str, dict]:
    """Ensure state['world']['npcs'] exists and return it."""
    w = state.setdefault("world", {})
    w.setdefault("npcs", {})
    return w["npcs"]


def get_npc(state: dict[str, Any], npc_id: str) -> dict | None:
    """Return NPC dict by id, or None."""
    return ensure_npcs(state).get(npc_id)


def get_npcs_in_location(state: dict[str, Any], location_id: str) -> list[dict]:
    """Return all NPCs whose location_id matches."""
    return [
        npc for npc in ensure_npcs(state).values()
        if npc.get("location_id") == location_id and npc.get("alive", True)
    ]


def apply_relationship_delta(state: dict[str, Any], npc_id: str, delta: int) -> int:
    """Adjust NPC relationship by delta, clamped to ±100. Returns new value."""
    npcs = ensure_npcs(state)
    npc = npcs.get(npc_id)
    if npc is None:
        return 0
    old = npc.get("relationship", 0)
    new = _clamp(old + delta, -100, 100)
    npc["relationship"] = new
    npc["disposition"] = _disposition_from_rel(new)
    return new


def record_npc_memory_event(state: dict[str, Any], npc_id: str, event_text: str) -> None:
    """Append a memory event to the NPC's memory list."""
    npc = get_npc(state, npc_id)
    if npc is None:
        return
    events = npc.setdefault("memory_events", [])
    events.append(event_text)


def maybe_refresh_npc_summary(state: dict[str, Any], npc_id: str) -> None:
    """Consolidate memory events if list gets long (>10 entries)."""
    npc = get_npc(state, npc_id)
    if npc is None:
        return
    events = npc.get("memory_events", [])
    if len(events) > 10:
        summary = "; ".join(events[-5:])
        npc["memory_events"] = [f"[Summary] {summary}"]


def shop_price_multiplier(state: dict[str, Any], npc_id: str) -> float:
    """1.0 base; relationship shifts price ±20%."""
    npc = get_npc(state, npc_id)
    if npc is None:
        return 1.0
    rel = npc.get("relationship", 0)
    # -20% at 100, +20% at -100, linear
    return round(1.0 - (rel / 500.0), 2)


def primary_merchant_npc_id(state: dict[str, Any]) -> str | None:
    """Return the first merchant NPC at the current location, or None."""
    loc = state.get("world", {}).get("location_id", "")
    for npc in get_npcs_in_location(state, loc):
        if npc.get("role") in ("merchant", "blacksmith", "healer", "trader"):
            return npc["id"]
    return None


def seed_world_npcs(state: dict[str, Any], rng: Any) -> None:
    """Populate NPCs from templates based on world setting."""
    npcs = ensure_npcs(state)
    if npcs:
        return  # already seeded

    templates = _load_json("npcs_seed_templates.json")
    setting = state.get("world_bible", {}).get("setting_primary", "medieval_fantasy")
    pool = templates.get(setting, templates.get("medieval_fantasy", {}))

    names = pool.get("names", [])
    roles = pool.get("roles", ["merchant", "guard", "innkeeper"])
    factions = pool.get("factions", [])
    locations = pool.get("locations", ["village_square", "market", "inn"])
    dispositions = pool.get("dispositions", ["neutral"])

    # Pick 5-10 NPCs
    count = rng.randint(5, min(10, len(names)))
    chosen_names = rng.sample(names, count)

    for i, name in enumerate(chosen_names):
        role = rng.choice(roles)
        faction = rng.choice(factions) if factions else ""
        loc = rng.choice(locations)
        disp = rng.choice(dispositions)
        npc_id = f"npc_{name.lower()}_{i}"
        npcs[npc_id] = {
            "id": npc_id,
            "name": name,
            "role": role,
            "faction": faction,
            "location_id": loc,
            "relationship": 0,
            "memory_events": [],
            "disposition": disp,
            "alive": True,
        }


def format_npc_sheet(npc: dict[str, Any]) -> str:
    """Format a single NPC's info as a readable string."""
    lines = [
        f"**{npc.get('name', 'Unknown')}**",
        f"  Role: {npc.get('role', 'unknown')}",
        f"  Faction: {npc.get('faction', 'none')}",
        f"  Disposition: {npc.get('disposition', 'neutral')}",
        f"  Relationship: {npc.get('relationship', 0)}",
        f"  Status: {'Alive' if npc.get('alive', True) else 'Dead'}",
    ]
    mem = npc.get("memory_events", [])
    if mem:
        lines.append(f"  Memories ({len(mem)}):")
        for m in mem[-3:]:
            lines.append(f"    - {m}")
    return "\n".join(lines)


def format_npcs_here(state: dict[str, Any]) -> str:
    """Format all NPCs at the current location."""
    loc = state.get("world", {}).get("location_id", "")
    npcs_here = get_npcs_in_location(state, loc)
    if not npcs_here:
        return "No one notable is here."
    parts = [f"**People here ({len(npcs_here)}):**"]
    for npc in npcs_here:
        disp_icon = {"friendly": "😊", "hostile": "😠", "neutral": "😐"}.get(
            npc.get("disposition", "neutral"), "😐"
        )
        parts.append(f"  {disp_icon} **{npc['name']}** — {npc.get('role', '')} (rel: {npc.get('relationship', 0)})")
    return "\n".join(parts)
