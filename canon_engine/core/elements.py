"""Canon Engine — Elemental Damage

Calculates final elemental damage after applying resistances, vulnerabilities,
immunities, and weather-based synergies.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Weather synergy table: (weather_condition, damage_type) → multiplier
# ---------------------------------------------------------------------------

_WEATHER_SYNERGY: dict[tuple[str, str], float] = {
    ("soaked", "lightning"): 1.5,
    ("wet", "frost"): 1.3,
    ("wet", "cold"): 1.3,
    ("storm", "frost"): 1.3,
    ("storm", "cold"): 1.3,
    ("storm", "lightning"): 1.25,
    ("rain", "lightning"): 1.25,
    ("rain", "cold"): 1.2,
    ("rain", "frost"): 1.2,
    # Fire in rain is weakened
    ("rain", "fire"): 0.75,
    ("storm", "fire"): 0.75,
    ("wet", "fire"): 0.75,
    ("soaked", "fire"): 0.5,
}


def calculate_elemental_damage(
    raw_damage: int,
    damage_type: str,
    target_resistances: dict[str, str] | None = None,
    weather_context: str | None = None,
) -> dict:
    """Apply elemental modifiers to *raw_damage*.

    Parameters
    ----------
    raw_damage : int
        Base damage before resistances/weather.
    damage_type : str
        Canonical damage type key (fire, cold, lightning, physical, …).
    target_resistances : dict[str, str] | None
        Mapping of damage_type → 'resistant' | 'vulnerable' | 'immune'.
    weather_context : str | None
        Current weather condition (rain, storm, soaked, wet, clear, …).

    Returns
    -------
    dict with keys: final_damage, resisted, weather_bonus, immunity
    """
    resists = target_resistances or {}
    weather = (weather_context or "").strip().lower()
    dmg_type = damage_type.strip().lower()

    final = float(raw_damage)
    resisted_amount = 0.0
    weather_bonus = 0.0
    immunity = False

    # --- Weather synergy ---
    syn_key = (weather, dmg_type)
    if syn_key in _WEATHER_SYNERGY:
        mult = _WEATHER_SYNERGY[syn_key]
        if mult > 1.0:
            weather_bonus = final * (mult - 1.0)
        else:
            weather_bonus = final * (mult - 1.0)  # negative = penalty
        final *= mult

    # --- Resistance / vulnerability / immunity ---
    resist_level = resists.get(dmg_type, "").lower()
    if resist_level == "immune":
        immunity = True
        resisted_amount = final
        final = 0.0
    elif resist_level == "resistant":
        resisted_amount = final * 0.5
        final *= 0.5
    elif resist_level == "vulnerable":
        bonus = final  # 100% more
        final *= 2.0
        resisted_amount = -bonus  # negative = extra damage taken

    return {
        "final_damage": max(0, int(final)),
        "resisted": max(0, int(resisted_amount)),
        "weather_bonus": int(weather_bonus),
        "immunity": immunity,
    }
