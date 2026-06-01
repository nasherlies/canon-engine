"""Canon Engine — Combat Math

D&D 2014 SRD dice mechanics: d20 rolls, attack/damage calculations,
proficiency scaling, AC, HP bar rendering, saving throws.
"""
from __future__ import annotations
import random
import math


# ---------------------------------------------------------------------------
# Dice
# ---------------------------------------------------------------------------

def d20(rng: random.Random | None = None) -> int:
    """Roll 1d20. Returns 1-20."""
    return (rng or random).randint(1, 20)


def roll_dice(n: int, sides: int, rng: random.Random | None = None) -> int:
    """Roll *n*d*sides* and return total."""
    _rng = rng or random
    return sum(_rng.randint(1, sides) for _ in range(n))


# ---------------------------------------------------------------------------
# Attack
# ---------------------------------------------------------------------------

def attack_roll(
    attacker_stat_mod: int,
    proficiency: int,
    rng: random.Random | None = None,
) -> tuple[int, bool, bool]:
    """Roll d20 + stat_mod + proficiency.

    Returns (total, is_crit, is_fumble).
    Natural 20 = critical hit (auto-hit, double dice).
    Natural 1  = fumble (auto-miss).
    """
    die = d20(rng)
    total = die + attacker_stat_mod + proficiency
    is_crit = die == 20
    is_fumble = die == 1
    return total, is_crit, is_fumble


def damage_roll(
    base_dice: tuple[int, int],
    ability_mod: int,
    is_crit: bool,
    rng: random.Random | None = None,
) -> int:
    """Roll weapon damage: NdS + ability_mod. On crit, dice are doubled (not the mod)."""
    n, sides = base_dice
    if is_crit:
        n *= 2
    return max(0, roll_dice(n, sides, rng) + ability_mod)


# ---------------------------------------------------------------------------
# Armour Class
# ---------------------------------------------------------------------------

def ac_calc(base_ac: int, dex_mod: int) -> int:
    """Simple AC: base + DEX mod."""
    return base_ac + dex_mod


# ---------------------------------------------------------------------------
# Proficiency
# ---------------------------------------------------------------------------

def proficiency_bonus(level: int) -> int:
    """D&D 5e proficiency bonus by character level."""
    if level < 1:
        level = 1
    if level <= 4:
        return 2
    if level <= 8:
        return 3
    if level <= 12:
        return 4
    if level <= 16:
        return 5
    return 6


# ---------------------------------------------------------------------------
# HP Bar
# ---------------------------------------------------------------------------

def render_hp_bar(current: int, maximum: int, width: int = 20) -> str:
    """Render a text HP bar like '████████░░░░░░░░░░░░'."""
    if maximum <= 0:
        return "░" * width
    ratio = max(0.0, min(1.0, current / maximum))
    filled = round(ratio * width)
    return "█" * filled + "░" * (width - filled)


# ---------------------------------------------------------------------------
# Saving Throw
# ---------------------------------------------------------------------------

def saving_throw(
    stat_mod: int,
    proficiency: int,
    rng: random.Random | None = None,
) -> tuple[int, bool]:
    """Roll a saving throw: d20 + stat_mod + proficiency.

    Returns (total, natural_20).
    """
    die = d20(rng)
    total = die + stat_mod + proficiency
    return total, die == 20
