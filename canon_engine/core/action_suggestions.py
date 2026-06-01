"""Canon Engine — Action Suggestion Chips

Generates context-sensitive action chips (quick-action buttons) for the UI.
Validates against a whitelist and supports tutorial-specific overrides.

Public API:
    layout_suggested_actions(state, narrator_suggestions) -> list[str]
    clear_suggestions(state) -> None
    hydrate_tutorial_suggestion_chips(state) -> list[str]
"""

from __future__ import annotations

from typing import Any


# ── Whitelist ───────────────────────────────────────────────────────────────

ACTION_WHITELIST: frozenset[str] = frozenset({
    "/say", "/do", "/look", "/scout", "/stealth", "/travel",
    "/think", "/talk", "/attack", "/inv", "/shop",
})

# ── Tutorial step → suggestion chip mapping ─────────────────────────────────

_TUTORIAL_CHIPS: dict[str, list[str]] = {
    "welcome": ["/look", "/inv"],
    "character_creation": ["/look"],
    "first_look": ["/look"],
    "movement": ["/travel", "/look"],
    "talking": ["/talk", "/look"],
    "first_quest": ["/talk", "/travel"],
    "inventory_basics": ["/inv", "/look"],
    "first_combat": ["/attack", "/inv"],
    "looting": ["/inv", "/look"],
    "crafting_intro": ["/inv", "/look"],
    "rest_and_save": ["/look", "/inv"],
    "tutorial_complete": ["/look", "/inv", "/attack", "/travel"],
    # Fallback IDs for minimal tutorial
    "inventory": ["/inv", "/look"],
    "combat": ["/attack", "/inv"],
    "skills": ["/inv", "/look"],
    "quest": ["/look", "/talk"],
    "save": ["/look", "/inv"],
    "npc": ["/talk", "/look"],
    "crafting": ["/inv", "/look"],
    "complete": ["/look", "/inv", "/attack", "/travel"],
}


# ── Public API ──────────────────────────────────────────────────────────────

def layout_suggested_actions(state: dict[str, Any], narrator_suggestions: list[str] | None = None) -> list[str]:
    """Build a list of validated action chips from narrator suggestions.

    Filters narrator-provided suggestions against the whitelist, then
    appends contextual defaults if fewer than 3 chips pass validation.

    Returns a list of action strings (e.g. ["/look", "/inv", "/attack"]).
    """
    chips: list[str] = []

    # Validate narrator suggestions against whitelist
    if narrator_suggestions:
        for suggestion in narrator_suggestions:
            normalized = suggestion.strip().lower()
            if not normalized.startswith("/"):
                normalized = "/" + normalized
            if normalized in ACTION_WHITELIST and normalized not in chips:
                chips.append(normalized)

    # Contextual defaults
    combat = state.get("combat", {})
    if combat.get("active", False):
        defaults = ["/attack", "/inv"]
    else:
        location = state.get("world", {}).get("location", "")
        defaults = ["/look", "/inv"]
        if location:
            defaults.append("/travel")

    for d in defaults:
        if d not in chips:
            chips.append(d)

    return chips[:6]  # Cap at 6 chips


def clear_suggestions(state: dict[str, Any]) -> None:
    """Remove suggestion chips from state."""
    state.pop("suggested_actions", None)


def hydrate_tutorial_suggestion_chips(state: dict[str, Any]) -> list[str]:
    """Return tutorial-specific suggestion chips based on current tutorial step.

    If the tutorial is not active, returns an empty list.
    """
    tut = state.get("tutorial", {})
    if not tut.get("active", False):
        return []

    steps = tut.get("steps", [])
    idx = tut.get("step_index", 0)

    if idx >= len(steps):
        return []

    current_step = steps[idx]
    step_id = current_step.get("id", "")

    chips = _TUTORIAL_CHIPS.get(step_id, ["/look"])

    # Store in state for UI consumption
    state["suggested_actions"] = list(chips)

    return list(chips)
