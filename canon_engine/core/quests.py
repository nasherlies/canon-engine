"""
Canon Engine — Procedural Quest System

Quest templates, generation, acceptance, progress tracking, and rewards.
Public API used by narrator, combat, economy, and travel systems.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

# ── Content loader ────────────────────────────────────────────────────

_CONTENT_DIR = Path(os.environ.get(
    "CANON_CONTENT_DIR",
    Path(__file__).resolve().parents[2] / "content",
))


def _load_json(name: str) -> dict:
    p = _CONTENT_DIR / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


# ── State helpers ─────────────────────────────────────────────────────

def _ensure_quests(state: dict[str, Any]) -> dict[str, list]:
    """Ensure state has active_quests, completed_quests, failed_quests."""
    state.setdefault("active_quests", [])
    state.setdefault("completed_quests", [])
    state.setdefault("failed_quests", [])
    return state


def _quest_by_id(state: dict[str, Any], quest_id: str) -> dict | None:
    """Find a quest by id across active/completed/failed."""
    for q in state.get("active_quests", []):
        if q.get("id") == quest_id:
            return q
    for q in state.get("completed_quests", []):
        if q.get("id") == quest_id:
            return q
    for q in state.get("failed_quests", []):
        if q.get("id") == quest_id:
            return q
    return None


def _generate_id(prefix: str = "q") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ── Template loading ──────────────────────────────────────────────────

def load_quest_templates() -> list[dict]:
    """Load all quest templates from content file."""
    data = _load_json("quest_templates.json")
    return data.get("quest_templates", [])


# ── Quest generation ──────────────────────────────────────────────────

def generate_quest_offer(state: dict[str, Any], npc_id: str, rng: Any) -> dict:
    """Pick a template, customize with state context, return a quest offer dict."""
    templates = load_quest_templates()
    if not templates:
        return {}

    tmpl = rng.choice(templates)
    level = state.get("player", {}).get("level", 1)
    variables = tmpl.get("variables", {})

    # Fill in template variables
    filled: dict[str, str] = {}
    for key, val in variables.items():
        if isinstance(val, list):
            filled[key] = rng.choice(val)
        elif isinstance(val, dict) and "count_min" in val:
            filled[key] = str(rng.randint(val["count_min"], val["count_max"]))
        else:
            filled[key] = str(val)

    # Build title and objectives
    title = tmpl.get("title_template", "Quest")
    for k, v in filled.items():
        title = title.replace("{" + k + "}", str(v))

    objectives = []
    for obj_tmpl in tmpl.get("objectives_template", []):
        text = obj_tmpl["text"]
        for k, v in filled.items():
            text = text.replace("{" + k + "}", str(v))
        target_count = obj_tmpl.get("count", 1)
        if isinstance(target_count, str) and target_count.startswith("{"):
            target_count = int(filled.get(target_count.strip("{}"), 1))
        objectives.append({
            "text": text,
            "target": obj_tmpl.get("target", ""),
            "count": int(target_count),
            "current": 0,
        })

    # Scale reward with level
    reward_base = tmpl.get("reward_base", {})
    gold = reward_base.get("gold", 10) + level * 5
    xp = reward_base.get("xp", 20) + level * 8
    reward = {"gold": gold, "xp": xp, "item": reward_base.get("item")}

    quest_id = _generate_id(tmpl.get("type", "q"))
    expires = tmpl.get("expires_turns")
    turn = state.get("turn", 0)

    return {
        "id": quest_id,
        "title": title,
        "giver": npc_id,
        "type": tmpl.get("type", "generic"),
        "objectives": objectives,
        "reward": reward,
        "status": "offered",
        "discovered_at": turn,
        "expires_at": (turn + expires) if expires else None,
    }


def offer_quests_for_npc(state: dict[str, Any], npc_id: str, rng: Any) -> list[dict]:
    """Generate 1-2 quest offers for an NPC."""
    count = rng.randint(1, 2)
    offers = []
    for _ in range(count):
        quest = generate_quest_offer(state, npc_id, rng)
        if quest:
            offers.append(quest)
    # Store offers in state temporarily
    state.setdefault("quest_offers", {})[npc_id] = offers
    return offers


def seed_merchant_quest_offers(state: dict[str, Any], rng: Any) -> None:
    """Generate quest offers for all merchant NPCs."""
    npcs = state.get("world", {}).get("npcs", {})
    for npc_id, npc in npcs.items():
        if npc.get("role") == "merchant" or npc.get("is_merchant"):
            offer_quests_for_npc(state, npc_id, rng)


# ── Quest lifecycle ───────────────────────────────────────────────────

def accept_quest(state: dict[str, Any], quest_id: str) -> dict:
    """Accept an offered quest. Returns result dict."""
    _ensure_quests(state)
    # Find in offers
    offers = state.get("quest_offers", {})
    quest = None
    for npc_offers in offers.values():
        for q in npc_offers:
            if q.get("id") == quest_id:
                quest = q
                break
        if quest:
            break

    if quest is None:
        return {"ok": False, "error": f"Quest offer '{quest_id}' not found."}

    quest["status"] = "active"
    state["active_quests"].append(quest)
    # Remove from offers
    for npc_id in offers:
        offers[npc_id] = [q for q in offers[npc_id] if q.get("id") != quest_id]

    return {"ok": True, "quest": quest, "message": f"Accepted: {quest['title']}"}


def abandon_quest(state: dict[str, Any], quest_id: str) -> dict:
    """Abandon an active quest."""
    _ensure_quests(state)
    active = state.get("active_quests", [])
    quest = None
    for q in active:
        if q.get("id") == quest_id:
            quest = q
            break

    if quest is None:
        return {"ok": False, "error": f"Active quest '{quest_id}' not found."}

    quest["status"] = "abandoned"
    state["active_quests"] = [q for q in active if q.get("id") != quest_id]
    state["failed_quests"].append(quest)

    return {"ok": True, "quest": quest, "message": f"Abandoned: {quest['title']}"}


def turn_in_quest(state: dict[str, Any], quest_id: str, rng: Any) -> dict:
    """Check objectives, grant rewards for a completed quest."""
    _ensure_quests(state)
    active = state.get("active_quests", [])
    quest = None
    for q in active:
        if q.get("id") == quest_id:
            quest = q
            break

    if quest is None:
        return {"ok": False, "error": f"Active quest '{quest_id}' not found."}

    # Check all objectives complete
    for obj in quest.get("objectives", []):
        if obj.get("current", 0) < obj.get("count", 1):
            return {
                "ok": False,
                "error": "Not all objectives complete.",
                "remaining": [
                    o["text"] for o in quest["objectives"]
                    if o.get("current", 0) < o.get("count", 1)
                ],
            }

    # Grant rewards
    reward = quest.get("reward", {})
    gold = reward.get("gold", 0)
    xp = reward.get("xp", 0)
    item = reward.get("item")

    player = state.setdefault("player", {})
    player["gold"] = player.get("gold", 0) + gold

    # Grant XP via leveling if available
    try:
        from canon_engine.core.leveling import add_xp
        add_xp(player, xp)
    except (ImportError, AttributeError):
        player["xp"] = player.get("xp", 0) + xp

    # Grant item
    if item:
        state.setdefault("inventory", []).append(item)

    # Move quest to completed
    quest["status"] = "completed"
    state["active_quests"] = [q for q in active if q.get("id") != quest_id]
    state["completed_quests"].append(quest)

    return {
        "ok": True,
        "quest": quest,
        "reward": {"gold": gold, "xp": xp, "item": item},
        "message": f"Completed: {quest['title']}! Earned {gold} gold, {xp} XP."
        + (f" Received: {item}." if item else ""),
    }


# ── Progress tracking ─────────────────────────────────────────────────

def update_quest_progress(state: dict[str, Any], event_type: str, event_data: dict) -> None:
    """Match an event to active quest objectives and update progress.

    event_type: 'kill', 'deliver', 'retrieve', 'travel', 'contact',
                'deliver_message', 'gather_clues', 'interview', 'confront',
                'return', 'obtain'
    event_data: dict with optional 'target', 'count' keys
    """
    for quest in state.get("active_quests", []):
        if quest.get("status") != "active":
            continue
        for obj in quest.get("objectives", []):
            if obj.get("target") == event_type:
                if obj.get("current", 0) < obj.get("count", 1):
                    increment = event_data.get("count", 1)
                    obj["current"] = min(
                        obj.get("current", 0) + increment,
                        obj.get("count", 1),
                    )


def fail_expired_quests(state: dict[str, Any], current_turn: int) -> list[str]:
    """Fail any active quests past their expiration. Returns list of failed quest titles."""
    _ensure_quests(state)
    failed_titles = []
    still_active = []
    for quest in state.get("active_quests", []):
        expires = quest.get("expires_at")
        if expires is not None and current_turn >= expires:
            quest["status"] = "expired"
            state["failed_quests"].append(quest)
            failed_titles.append(quest.get("title", "Unknown Quest"))
        else:
            still_active.append(quest)
    state["active_quests"] = still_active
    return failed_titles


# ── Display formatting ────────────────────────────────────────────────

def format_quest_list(state: dict[str, Any]) -> str:
    """Format all active quests as a readable list."""
    _ensure_quests(state)
    active = state.get("active_quests", [])
    if not active:
        return "No active quests."

    lines = ["**Active Quests:**"]
    for q in active:
        objs_done = sum(1 for o in q.get("objectives", []) if o.get("current", 0) >= o.get("count", 1))
        objs_total = len(q.get("objectives", []))
        status_str = f"[{objs_done}/{objs_total}]"
        expires = q.get("expires_at")
        exp_str = f" (expires turn {expires})" if expires else ""
        lines.append(f"• **{q['title']}** {status_str}{exp_str}")
    return "\n".join(lines)


def format_quest_detail(state: dict[str, Any], quest_id: str) -> str:
    """Format detailed view of a single quest."""
    quest = _quest_by_id(state, quest_id)
    if quest is None:
        return f"Quest '{quest_id}' not found."

    lines = [f"**{quest['title']}**"]
    lines.append(f"Type: {quest.get('type', 'unknown')}")
    lines.append(f"Giver: {quest.get('giver', 'unknown')}")
    lines.append(f"Status: {quest.get('status', 'unknown')}")
    lines.append("")
    lines.append("**Objectives:**")
    for obj in quest.get("objectives", []):
        cur = obj.get("current", 0)
        cnt = obj.get("count", 1)
        check = "✅" if cur >= cnt else "⬜"
        lines.append(f"  {check} {obj.get('text', '?')} ({cur}/{cnt})")

    reward = quest.get("reward", {})
    lines.append("")
    lines.append(f"**Reward:** {reward.get('gold', 0)} gold, {reward.get('xp', 0)} XP")
    if reward.get("item"):
        lines.append(f"  + Item: {reward['item']}")

    expires = quest.get("expires_at")
    if expires:
        lines.append(f"\n*Expires at turn {expires}*")

    return "\n".join(lines)


# ── NPC interactions ──────────────────────────────────────────────────

def resolve_gift(state: dict[str, Any], item_name: str, npc_id: str) -> dict:
    """Give an item to an NPC. Returns result dict."""
    inventory = state.get("inventory", [])
    if item_name not in inventory:
        return {"ok": False, "error": f"You don't have '{item_name}' in your inventory."}

    # Remove from inventory
    inventory.remove(item_name)

    # Boost relationship
    try:
        from canon_engine.core.npc import apply_relationship_delta
        new_rel = apply_relationship_delta(state, npc_id, 10)
    except (ImportError, AttributeError):
        new_rel = 0

    return {
        "ok": True,
        "message": f"You give {item_name} to {npc_id}. They seem grateful.",
        "relationship": new_rel,
    }


def resolve_threaten(state: dict[str, Any], npc_id: str, rng: Any) -> dict:
    """Attempt to threaten an NPC. CHA check against their willpower."""
    player = state.get("player", {})
    cha = player.get("stats", {}).get("CHA", 10)

    # Target DC based on NPC relationship
    try:
        from canon_engine.core.npc import get_npc
        npc = get_npc(state, npc_id)
    except (ImportError, AttributeError):
        npc = None

    if npc is None:
        return {"ok": False, "error": f"NPC '{npc_id}' not found."}

    rel = npc.get("relationship", 0)
    # Friendly NPCs are harder to threaten (DC 15), hostile are easier (DC 8)
    if rel >= 30:
        dc = 15
    elif rel <= -30:
        dc = 8
    else:
        dc = 12

    roll = rng.randint(1, 20)
    total = roll + (cha - 10) // 2
    success = total >= dc

    if success:
        try:
            from canon_engine.core.npc import apply_relationship_delta
            apply_relationship_delta(state, npc_id, -20)
        except (ImportError, AttributeError):
            pass
        return {
            "ok": True,
            "success": True,
            "roll": roll,
            "dc": dc,
            "message": f"Intimidation successful! (rolled {roll}, needed {dc}). {npc_id} backs down.",
        }
    else:
        try:
            from canon_engine.core.npc import apply_relationship_delta
            apply_relationship_delta(state, npc_id, -15)
        except (ImportError, AttributeError):
            pass
        return {
            "ok": True,
            "success": False,
            "roll": roll,
            "dc": dc,
            "message": f"Intimidation failed! (rolled {roll}, needed {dc}). {npc_id} is not impressed.",
        }
