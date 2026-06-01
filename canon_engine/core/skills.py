"""Canon Engine — Skill Trees System

Four skill trees (warrior, rogue, mage, ranger) with unlock and use mechanics.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Content path
# ---------------------------------------------------------------------------

_CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "content"


# ---------------------------------------------------------------------------
# Skill tree loading
# ---------------------------------------------------------------------------

def load_skill_trees() -> dict[str, Any]:
    """Load skill trees from content/skills_trees.json."""
    path = _CONTENT_DIR / "skills_trees.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("skill_trees", {})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_unlocked_skills(state: dict[str, Any]) -> set[str]:
    """Return the set of unlocked skill IDs."""
    return set(state.get("unlocked_skills", []))


def _get_skill_points(state: dict[str, Any]) -> int:
    """Return available skill points."""
    return state.get("skill_points", 0)


def _find_skill(skill_trees: dict[str, Any], skill_id: str) -> tuple[str, dict[str, Any]] | tuple[None, None]:
    """Find a skill across all trees. Returns (tree_id, skill_dict) or (None, None)."""
    for tree_id, tree in skill_trees.items():
        skills = tree.get("skills", {})
        if skill_id in skills:
            return tree_id, skills[skill_id]
    return None, None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_available_skills(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return skills where prerequisites are met and a skill point is available."""
    skill_trees = load_skill_trees()
    unlocked = _get_unlocked_skills(state)
    points = _get_skill_points(state)
    available = []

    for tree_id, tree in skill_trees.items():
        skills = tree.get("skills", {})
        for skill_id, skill in skills.items():
            if skill_id in unlocked:
                continue
            if points < skill.get("cost", 1):
                continue
            # Check prerequisites
            prereqs = skill.get("prerequisites", [])
            if all(p in unlocked for p in prereqs):
                available.append({**skill, "tree": tree_id})

    return available


def resolve_unlock(state: dict[str, Any], skill_id: str) -> dict[str, Any]:
    """Spend 1 skill point to unlock a skill.

    Returns {ok, skill_id, message}.
    """
    skill_trees = load_skill_trees()
    unlocked = _get_unlocked_skills(state)
    tree_id, skill = _find_skill(skill_trees, skill_id)

    if skill is None:
        return {"ok": False, "skill_id": skill_id, "message": f"Unknown skill: {skill_id}"}

    if skill_id in unlocked:
        return {"ok": False, "skill_id": skill_id, "message": f"Skill '{skill.get('name', skill_id)}' is already unlocked."}

    cost = skill.get("cost", 1)
    points = _get_skill_points(state)
    if points < cost:
        return {"ok": False, "skill_id": skill_id, "message": f"Not enough skill points. Need {cost}, have {points}."}

    prereqs = skill.get("prerequisites", [])
    for prereq in prereqs:
        if prereq not in unlocked:
            return {"ok": False, "skill_id": skill_id, "message": f"Missing prerequisite: {prereq}"}

    # Unlock
    state.setdefault("unlocked_skills", []).append(skill_id)
    state["skill_points"] = points - cost

    return {
        "ok": True,
        "skill_id": skill_id,
        "message": f"Unlocked **{skill.get('name', skill_id)}**!",
    }


def resolve_use_skill(
    state: dict[str, Any],
    skill_id: str,
    target: dict[str, Any] | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Activate a skill's effect.

    Returns {ok, skill_id, effects, message}.
    """
    _rng = rng or random.Random()
    unlocked = _get_unlocked_skills(state)

    if skill_id not in unlocked:
        return {"ok": False, "skill_id": skill_id, "message": f"Skill '{skill_id}' is not unlocked."}

    skill_trees = load_skill_trees()
    tree_id, skill = _find_skill(skill_trees, skill_id)
    if skill is None:
        return {"ok": False, "skill_id": skill_id, "message": f"Unknown skill: {skill_id}"}

    effects = skill.get("effects", {})
    etype = effects.get("type", "passive")
    messages = []

    # Apply skill effects based on type
    if etype == "active":
        # Process active effects
        if effects.get("splash_damage"):
            targets = effects.get("targets", 2)
            messages.append(f"Cleave hits {targets} targets for {effects.get('damage_mult', 0.75) * 100:.0f}% damage each.")

        if effects.get("stun_duration"):
            messages.append(f"Shield Bash stuns target for {effects['stun_duration']} turn(s).")

        if effects.get("ac_bonus"):
            dur = effects.get("duration", 2)
            messages.append(f"Fortify grants +{effects['ac_bonus']} AC for {dur} turns.")
            # Apply a temporary AC bonus status
            state.setdefault("temp_buffs", []).append({
                "name": "fortify",
                "ac_bonus": effects["ac_bonus"],
                "remaining": dur,
            })

        if effects.get("damage_mult") and effects.get("ac_penalty_pct"):
            mult = effects["damage_mult"]
            penalty = effects["ac_penalty_pct"]
            dur = effects.get("duration", 3)
            messages.append(f"Berserker Rage! +{(mult - 1) * 100:.0f}% damage, -{penalty * 100:.0f}% AC for {dur} turns.")
            state.setdefault("temp_buffs", []).append({
                "name": "berserker_rage",
                "damage_mult": mult,
                "ac_penalty_pct": penalty,
                "remaining": dur,
            })

        if effects.get("damage_mult") and effects.get("requires_stealth"):
            mult = effects["damage_mult"]
            messages.append(f"Backstab! {mult}x damage from stealth.")

        if effects.get("guaranteed_flee"):
            messages.append("Smoke Bomb! You flee safely.")
            combat = state.get("combat", {})
            combat["active"] = False

        if effects.get("steal_gold"):
            dc = effects.get("dc_base", 12)
            dex_mod = (state.get("stats", {}).get("DEX", 10) - 10) // 2
            roll = _rng.randint(1, 20)
            total = roll + dex_mod
            if total >= dc:
                stolen = _rng.randint(5, 25)
                state["gold"] = state.get("gold", 0) + stolen
                messages.append(f"Pickpocket success! Stolen {stolen} gold. (Rolled {total} vs DC {dc})")
            else:
                messages.append(f"Pickpocket failed! (Rolled {total} vs DC {dc})")

        if effects.get("reveal_stats"):
            if target:
                name = target.get("name", target.get("type", "enemy"))
                hp = target.get("hp", "?")
                ac = target.get("ac", "?")
                messages.append(f"Analyze: **{name}** — HP: {hp}, AC: {ac}")
            else:
                messages.append("Analyze: No target to analyze.")

        if effects.get("spell_damage_mult"):
            mult = effects["spell_damage_mult"]
            dur = effects.get("duration", 1)
            messages.append(f"Amplify! +{(mult - 1) * 100:.0f}% spell damage for {dur} turn(s).")
            state.setdefault("temp_buffs", []).append({
                "name": "amplify",
                "spell_damage_mult": mult,
                "remaining": dur,
            })

        if effects.get("absorb_damage"):
            absorb = effects["absorb_damage"]
            dur = effects.get("duration", 3)
            messages.append(f"Barrier absorbs up to {absorb} damage for {dur} turns.")
            state.setdefault("temp_buffs", []).append({
                "name": "barrier",
                "absorb_remaining": absorb,
                "remaining": dur,
            })

        if effects.get("tame_beast"):
            dc = effects.get("dc_base", 14)
            cha_mod = (state.get("stats", {}).get("CHA", 10) - 10) // 2
            roll = _rng.randint(1, 20)
            total = roll + cha_mod
            if total >= dc:
                messages.append(f"Beast Bond success! A beast joins you as a companion. (Rolled {total} vs DC {dc})")
                state.setdefault("companions", []).append({"name": "Beast Companion", "type": "beast"})
            else:
                messages.append(f"Beast Bond failed. (Rolled {total} vs DC {dc})")

    # Passive effects are handled by get_passive_effects

    if not messages:
        messages.append(f"Used **{skill.get('name', skill_id)}**.")

    return {
        "ok": True,
        "skill_id": skill_id,
        "effects": effects,
        "message": " ".join(messages),
    }


def get_passive_effects(state: dict[str, Any]) -> dict[str, Any]:
    """Aggregate passive bonuses from all unlocked skills.

    Returns a dict of bonus keys and their total values.
    """
    skill_trees = load_skill_trees()
    unlocked = _get_unlocked_skills(state)
    bonuses: dict[str, Any] = {
        "scavenge_bonus": 0.0,
        "scout_dc_reduction": 0,
        "perception_bonus": 0,
        "ignore_resistance": False,
        "detect_hidden": False,
    }

    for tree_id, tree in skill_trees.items():
        skills = tree.get("skills", {})
        for skill_id, skill in skills.items():
            if skill_id not in unlocked:
                continue
            effects = skill.get("effects", {})
            if effects.get("type") != "passive":
                continue

            if "scavenge_bonus" in effects:
                bonuses["scavenge_bonus"] += effects["scavenge_bonus"]
            if "scout_dc_reduction" in effects:
                bonuses["scout_dc_reduction"] += effects["scout_dc_reduction"]
            if "perception_bonus" in effects:
                bonuses["perception_bonus"] += effects["perception_bonus"]
            if effects.get("ignore_resistance"):
                bonuses["ignore_resistance"] = True
            if effects.get("detect_hidden"):
                bonuses["detect_hidden"] = True

    return bonuses


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def format_skills(state: dict[str, Any]) -> str:
    """Format the player's skill status for display."""
    skill_trees = load_skill_trees()
    unlocked = _get_unlocked_skills(state)
    points = _get_skill_points(state)

    lines = [f"**Skill Points:** {points}", ""]

    for tree_id, tree in skill_trees.items():
        tree_name = tree.get("name", tree_id)
        lines.append(f"**{tree_name}**")
        skills = tree.get("skills", {})
        for skill_id, skill in skills.items():
            name = skill.get("name", skill_id)
            if skill_id in unlocked:
                lines.append(f"  ✅ {name}")
            else:
                prereqs = skill.get("prerequisites", [])
                prereq_str = f" (requires: {', '.join(prereqs)})" if prereqs else ""
                lines.append(f"  🔒 {name} [{skill.get('cost', 1)} SP]{prereq_str}")
        lines.append("")

    return "\n".join(lines)
