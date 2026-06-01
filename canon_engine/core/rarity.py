"""Rarity tiers with weighted rolling."""

from __future__ import annotations

import random

# 8 tiers: (rank, hex color, drop weight)
RARITY_MAP: dict[str, dict] = {
    "dirt":     {"rank": 0, "color": "#444444", "weight": 30},
    "common":   {"rank": 1, "color": "#aaaaaa", "weight": 35},
    "uncommon": {"rank": 2, "color": "#55cc55", "weight": 18},
    "power":    {"rank": 3, "color": "#5599ff", "weight": 10},
    "rare":     {"rank": 4, "color": "#cc55cc", "weight": 4},
    "epic":     {"rank": 5, "color": "#ff8800", "weight": 2},
    "mythical": {"rank": 6, "color": "#ffd700", "weight": 0.8},
    "god":      {"rank": 7, "color": "#ff2222", "weight": 0.2},
}

# Ordered list for weighted selection
_TIER_NAMES = ["dirt", "common", "uncommon", "power", "rare", "epic", "mythical", "god"]


def roll_rarity(rng: random.Random, luck_mod: int = 0) -> str:
    """Weighted random pick.  Luck shifts weights toward rarer tiers."""
    weights = []
    for name in _TIER_NAMES:
        w = RARITY_MAP[name]["weight"]
        # Luck bonus: each +1 luck_mod gives a small boost to rare+ tiers
        rank = RARITY_MAP[name]["rank"]
        if rank >= 4 and luck_mod > 0:
            w += luck_mod * 0.3
        elif rank <= 1 and luck_mod > 0:
            w = max(w - luck_mod * 0.5, 0.1)
        elif luck_mod < 0 and rank >= 4:
            w = max(w + luck_mod * 0.2, 0.05)
        elif luck_mod < 0 and rank <= 1:
            w += abs(luck_mod) * 0.3
        weights.append(w)
    return rng.choices(_TIER_NAMES, weights=weights, k=1)[0]


def is_notable(rarity: str) -> bool:
    """Rare or above."""
    info = RARITY_MAP.get(rarity)
    if info is None:
        return False
    return info["rank"] >= 4


def is_mythical(rarity: str) -> bool:
    """Mythical or above."""
    info = RARITY_MAP.get(rarity)
    if info is None:
        return False
    return info["rank"] >= 6
