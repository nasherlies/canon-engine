"""
Story Branching System for Canon Engine.

Tracks major player choices as narrative branch nodes and generates
delayed consequences that make decisions feel meaningful.

Usage:
    from canon_engine.systems.story_branch import (
        record_choice,
        check_consequences,
        get_branch_summary,
        handle_choices_command,
        handle_consequences_command,
    )

Choices are stored in ``state['story_branches']`` as a list of dicts:
    {
        "id":           str,          # unique choice identifier
        "description":  str,          # human-readable description of the choice
        "timestamp":    str,          # ISO-8601 timestamp
        "scene_number": int,          # scene when the choice was made
        "consequences": list[dict],   # list of consequence entries
        "triggered":    list[str],    # IDs of consequences already triggered
    }

Each consequence dict:
    {
        "id":            str,         # unique consequence identifier
        "description":   str,         # what happens when triggered
        "trigger_after": int,         # how many scenes after the choice before eligible
        "trigger_context": str|None,  # optional context keyword that must match
        "triggered":     bool,        # has this consequence fired yet?
    }
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_branches(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Ensure state has a story_branches list and return it."""
    if "story_branches" not in state:
        state["story_branches"] = []
    return state["story_branches"]


def _current_scene(state: Dict[str, Any]) -> int:
    """Return the current scene/turn number from state."""
    return int(state.get("scene_number", state.get("turn", 0)))


def _make_consequence(
    description: str,
    trigger_after: int = 0,
    trigger_context: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a normalised consequence dict."""
    return {
        "id": f"cons_{uuid.uuid4().hex[:8]}",
        "description": description,
        "trigger_after": max(0, int(trigger_after)),
        "trigger_context": trigger_context,
        "triggered": False,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def record_choice(
    state: Dict[str, Any],
    choice_id: str,
    description: str,
    consequences: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Record a major story decision in the game state.

    Parameters
    ----------
    state : dict
        The mutable game session state.
    choice_id : str
        A unique identifier for this choice (e.g. ``"spare_bandit"``).
    description : str
        A human-readable summary (e.g. *"You chose to spare the bandit's life."*).
    consequences : list, optional
        Each item is either:
        - a plain string (immediate consequence, triggers next scene), or
        - a dict with keys ``description``, ``trigger_after``, ``trigger_context``.

    Returns
    -------
    dict
        The newly created branch node.
    """
    branches = _ensure_branches(state)
    scene = _current_scene(state)

    normalised: List[Dict[str, Any]] = []
    for c in (consequences or []):
        if isinstance(c, str):
            normalised.append(_make_consequence(c))
        elif isinstance(c, dict):
            normalised.append(_make_consequence(
                description=c.get("description", ""),
                trigger_after=c.get("trigger_after", 0),
                trigger_context=c.get("trigger_context"),
            ))
        else:
            normalised.append(_make_consequence(str(c)))

    node = {
        "id": choice_id,
        "description": description,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scene_number": scene,
        "consequences": normalised,
        "triggered": [],
    }
    branches.append(node)
    return node


def check_consequences(
    state: Dict[str, Any],
    current_context: str = "",
) -> List[Dict[str, Any]]:
    """
    Check all un-triggered consequences and return those that should fire now.

    A consequence fires when **both** conditions are met:
    1. Enough scenes have elapsed since the choice (``current_scene - choice_scene >= trigger_after``).
    2. If ``trigger_context`` is set, it must appear as a substring of ``current_context``
       (case-insensitive).

    Triggered consequences are marked so they won't fire again.

    Parameters
    ----------
    state : dict
        The mutable game session state.
    current_context : str
        A short description of the current scene / location / NPC, used to
        match contextual triggers (e.g. ``"bandit_camp"``, ``"royal_court"``).

    Returns
    -------
    list[dict]
        Consequences that fired this call.  Each dict has ``choice_id``,
        ``choice_description``, and the consequence ``description``.
    """
    branches = _ensure_branches(state)
    scene = _current_scene(state)
    ctx_lower = current_context.lower()
    fired: List[Dict[str, Any]] = []

    for branch in branches:
        choice_id = branch["id"]
        choice_scene = branch["scene_number"]

        for cons in branch["consequences"]:
            if cons["triggered"]:
                continue

            # Scene-gate
            if (scene - choice_scene) < cons["trigger_after"]:
                continue

            # Context-gate (if specified)
            if cons["trigger_context"]:
                if cons["trigger_context"].lower() not in ctx_lower:
                    continue

            # Fire it
            cons["triggered"] = True
            branch["triggered"].append(cons["id"])
            fired.append({
                "choice_id": choice_id,
                "choice_description": branch["description"],
                "consequence": cons["description"],
            })

    return fired


def get_branch_summary(state: Dict[str, Any]) -> str:
    """
    Produce a human-readable summary of the story's branching history.

    Useful for session recaps, ``/summary`` commands, or narrator context.

    Returns
    -------
    str
        A formatted multi-line string.
    """
    branches = _ensure_branches(state)
    if not branches:
        return "No major decisions have been recorded yet."

    lines: List[str] = ["📜 **Story Branch Summary**", ""]

    for i, branch in enumerate(branches, 1):
        ts = branch.get("timestamp", "unknown")
        # Show date portion only for readability
        try:
            date_str = ts[:10]
        except Exception:
            date_str = ts

        lines.append(f"**{i}. {branch['description']}**")
        lines.append(f"   _Scene {branch.get('scene_number', '?')}_ · {date_str}")

        triggered = [c for c in branch["consequences"] if c["triggered"]]
        pending = [c for c in branch["consequences"] if not c["triggered"]]

        if triggered:
            lines.append("   ↳ Consequences revealed:")
            for c in triggered:
                lines.append(f"     • {c['description']}")
        if pending:
            lines.append(f"   ↳ {len(pending)} consequence(s) pending…")

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Command handlers (for integration with command_parser)
# ---------------------------------------------------------------------------

def handle_choices_command(state: Dict[str, Any]) -> str:
    """
    Handle the ``/choices`` command — show the player's decision history.

    Returns a formatted string suitable for display.
    """
    branches = _ensure_branches(state)
    if not branches:
        return "You haven't made any major story decisions yet."

    lines: List[str] = ["⚔️ **Your Decisions**", ""]
    for i, branch in enumerate(branches, 1):
        scene = branch.get("scene_number", "?")
        lines.append(f"{i}. **{branch['description']}** _(scene {scene})_")
    lines.append("")
    lines.append(f"_Total choices: {len(branches)}_")
    return "\n".join(lines)


def handle_consequences_command(state: Dict[str, Any]) -> str:
    """
    Handle the ``/consequences`` command — show active/pending consequences.

    Returns a formatted string suitable for display.
    """
    branches = _ensure_branches(state)
    if not branches:
        return "No consequences are in play — your story is still unfolding."

    revealed: List[str] = []
    pending: List[str] = []

    for branch in branches:
        for cons in branch["consequences"]:
            entry = (
                f"• {cons['description']} "
                f"— _from: {branch['description']}_"
            )
            if cons["triggered"]:
                revealed.append(entry)
            else:
                when = "next scene" if cons["trigger_after"] == 0 else \
                    f"in ~{cons['trigger_after']} scene(s)"
                ctx = f" when '{cons['trigger_context']}'" if cons["trigger_context"] else ""
                pending.append(f"{entry}  ⏳ _{when}{ctx}_")

    parts: List[str] = ["🔮 **Consequences**", ""]
    if revealed:
        parts.append("**Revealed:**")
        parts.extend(revealed)
        parts.append("")
    if pending:
        parts.append("**Pending:**")
        parts.extend(pending)
    else:
        parts.append("_No pending consequences._")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

_TEMPLATES_PATH = Path(__file__).resolve().parents[2] / "content" / "story_templates.json"


def load_templates(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load story choice/consequence templates from JSON."""
    p = path or _TEMPLATES_PATH
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def record_from_template(
    state: Dict[str, Any],
    template_id: str,
    overrides: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Record a choice from a template by ID.  Returns the branch node or None.
    """
    templates = load_templates()
    tpl = next((t for t in templates if t["id"] == template_id), None)
    if tpl is None:
        return None

    desc = (overrides or {}).get("description", tpl["description"])
    cons = tpl.get("consequences", [])
    return record_choice(state, template_id, desc, cons)
