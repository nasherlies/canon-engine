"""Canon Engine — Boss Encounter System

Boss encounters with phases, special abilities, and death loot.
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
# Boss loading
# ---------------------------------------------------------------------------

def load_bosses() -> dict[str, Any]:
    """Load boss definitions from content/bosses.json."""
    path = _CONTENT_DIR / "bosses.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("bosses", {})


def is_boss(enemy_id: str) -> bool:
    """Check if an enemy ID corresponds to a boss."""
    bosses = load_bosses()
    return enemy_id in bosses


# ---------------------------------------------------------------------------
# Phase management
# ---------------------------------------------------------------------------

def get_boss_phase(boss: dict[str, Any], hp_pct: float) -> int:
    """Determine which phase (1-indexed) a boss is in based on HP percentage.

    Phase thresholds are checked from last to first; the first threshold
    that hp_pct meets or exceeds determines the phase.

    Returns 1-based phase number (1 = first phase).
    """
    phases = boss.get("phases", [])
    if not phases:
        return 1

    # Phase boundaries: phase N activates when hp_pct <= thresholds[N]
    # Thresholds descend (1.0, 0.6, 0.3). Check from last to first.
    # At 100% → phase 1, at 55% → phase 2, at 25% → phase 3
    # At exact threshold, you enter the next phase (0.6 → phase 2, 0.3 → phase 3)
    for i in range(len(phases) - 1, 0, -1):
        threshold = phases[i].get("threshold", 0.0)
        if hp_pct <= threshold:
            return i + 1
    return 1


def get_current_phase_data(boss: dict[str, Any], hp_pct: float) -> dict[str, Any]:
    """Return the phase dict for the current HP percentage."""
    phases = boss.get("phases", [])
    if not phases:
        return {}

    current_phase = get_boss_phase(boss, hp_pct)
    idx = current_phase - 1
    if 0 <= idx < len(phases):
        return phases[idx]
    return phases[-1] if phases else {}


# ---------------------------------------------------------------------------
# Boss abilities
# ---------------------------------------------------------------------------

def resolve_boss_ability(
    boss: dict[str, Any],
    phase: int,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Select and resolve a boss special ability for the given phase.

    Returns {ability, description, damage}.
    """
    _rng = rng or random.Random()

    phases = boss.get("phases", [])
    if not phases:
        return {"ability": "attack", "description": "The boss attacks!", "damage": 0}

    idx = phase - 1
    if idx < 0 or idx >= len(phases):
        idx = len(phases) - 1

    phase_data = phases[idx]
    abilities = phase_data.get("abilities", [])

    if not abilities:
        return {"ability": "attack", "description": "The boss attacks!", "damage": 0}

    ability_id = _rng.choice(abilities)

    # Generate a description and damage based on the ability
    ability_descriptions = {
        "bone_storm": {"description": "The Skeleton King summons a whirlwind of bones!", "damage": _rng.randint(8, 20), "damage_type": "physical"},
        "summon_skeletons": {"description": "Skeleton minions rise from the ground!", "damage": 0, "damage_type": "physical", "summons": 2},
        "death_beam": {"description": "A beam of necrotic energy lances toward you!", "damage": _rng.randint(15, 30), "damage_type": "necrotic"},
        "grave_slash": {"description": "A devastating slash wreathed in dark energy!", "damage": _rng.randint(10, 22), "damage_type": "slashing"},
        "necrotic_burst": {"description": "Dark energy erupts outward!", "damage": _rng.randint(12, 24), "damage_type": "necrotic"},
        "life_drain": {"description": "The Crypt Lord drains your life force!", "damage": _rng.randint(10, 20), "damage_type": "necrotic", "heal_self": True},
        "death_scream": {"description": "A psychic scream tears through your mind!", "damage": _rng.randint(12, 24), "damage_type": "psychic"},
        "final_strike": {"description": "A devastating final blow!", "damage": _rng.randint(18, 38), "damage_type": "slashing"},
        "shadow_tendrils": {"description": "Tendrils of darkness lash out!", "damage": _rng.randint(10, 20), "damage_type": "necrotic"},
        "mirror_shadows": {"description": "Shadow clones appear!", "damage": 0, "damage_type": "physical", "summons": 2},
        "shadow_step": {"description": "The Shadow King teleports behind you!", "damage": _rng.randint(12, 24), "damage_type": "necrotic"},
        "void_blade": {"description": "A blade of pure void strikes!", "damage": _rng.randint(16, 30), "damage_type": "necrotic"},
        "reality_tear": {"description": "Reality itself tears apart!", "damage": _rng.randint(20, 40), "damage_type": "necrotic"},
        "shadow_consume": {"description": "Shadows consume your essence!", "damage": _rng.randint(18, 36), "damage_type": "necrotic", "heal_self": True},
    }

    info = ability_descriptions.get(ability_id, {
        "description": f"The boss uses {ability_id}!",
        "damage": _rng.randint(5, 15),
        "damage_type": "physical",
    })

    return {
        "ability": ability_id,
        "description": info.get("description", f"Uses {ability_id}"),
        "damage": info.get("damage", 0),
        "damage_type": info.get("damage_type", "physical"),
        "heal_self": info.get("heal_self", False),
        "summons": info.get("summons", 0),
    }


# ---------------------------------------------------------------------------
# Boss loot
# ---------------------------------------------------------------------------

def apply_boss_death_loot(
    state: dict[str, Any],
    boss: dict[str, Any],
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Apply loot and XP from a defeated boss.

    Rolls for each loot item based on drop_chance (if present, else 100%).

    Returns {xp, loot, gold, message}.
    """
    _rng = rng or random.Random()

    # Grant XP
    xp = boss.get("xp", 0)
    state["xp"] = state.get("xp", 0) + xp

    # Roll loot
    loot_drops: list[dict[str, Any]] = []
    loot_table = boss.get("loot", [])

    for loot_entry in loot_table:
        drop_chance = loot_entry.get("drop_chance", 1.0)
        roll = _rng.random()
        if roll <= drop_chance:
            item = dict(loot_entry)
            state.setdefault("inventory", []).append(item)
            loot_drops.append(item)

    # Gold reward — scale with boss XP
    gold = _rng.randint(xp // 10, xp // 5)
    state["gold"] = state.get("gold", 0) + gold

    loot_names = [item.get("name", "Unknown") for item in loot_drops]
    msg_parts = [f"**{boss.get('name', 'Boss')}** defeated!"]
    if xp > 0:
        msg_parts.append(f"+{xp} XP")
    if gold > 0:
        msg_parts.append(f"+{gold} gold")
    if loot_names:
        msg_parts.append(f"Loot: {', '.join(loot_names)}")

    return {
        "xp": xp,
        "loot": loot_drops,
        "gold": gold,
        "message": " ".join(msg_parts),
    }
