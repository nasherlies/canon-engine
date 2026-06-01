"""Canon Engine — Minigames: Lockpick and Gamble

Lockpick: DEX check vs lock DC (8-18), window of 3 on d20.
Gamble: Bet gold, d20 vs opponent, higher wins.
"""

from __future__ import annotations

import random
from typing import Any

from canon_engine.core.stats import get_stat_modifier


# ── Lockpick ────────────────────────────────────────────────────────────────

def resolve_lockpick(state: dict[str, Any], rng: Any = None) -> dict:
    """DEX check vs lock DC (8-18), window of 3 on d20.

    The player rolls a d20 + DEX modifier.  If the roll falls within a
    *window* of 3 around the DC (DC-1 to DC+1 for base window, expanded
    by DEX modifier), the lock opens.  Below the window: jam.  Above: break.

    Returns a result dict with keys: success, roll, dc, window_low, window_high,
    outcome, description.
    """
    _rng = rng or random.Random()

    player_stats = state.get("player", {}).get("stats")
    stats = player_stats if player_stats else state.get("stats", {})
    dex = stats.get("DEX", 10)
    dex_mod = get_stat_modifier(dex)

    roll = _rng.randint(1, 20)
    total = roll + dex_mod

    # Lock DC ranges 8-18 depending on context
    dc = state.get("minigame", {}).get("lock_dc", 12)
    dc = max(8, min(18, dc))

    # Window of 3 centered on DC (DC-1 to DC+1), widened by dex_mod
    window_low = dc - 1 + min(0, dex_mod)  # negative mod narrows
    window_high = dc + 1 + max(0, dex_mod)  # positive mod widens
    # Ensure window is at least 3 wide
    if window_high - window_low < 2:
        window_high = window_low + 2

    if window_low <= total <= window_high:
        outcome = "open"
        desc = f"You deftly pick the lock! (Rolled {total} vs DC {dc}, window {window_low}-{window_high})"
    elif total < window_low:
        outcome = "jam"
        desc = f"The pick jams in the lock! (Rolled {total}, below window {window_low}-{window_high})"
    else:
        outcome = "break"
        desc = f"Too much force — the pick snaps! (Rolled {total}, above window {window_low}-{window_high})"

    # Consume lockpick from inventory on failure
    if outcome != "open":
        inv = state.get("inventory", [])
        for i, item in enumerate(inv):
            if isinstance(item, str) and "lockpick" in item.lower():
                inv.pop(i)
                break

    # Clear minigame state
    state.pop("minigame", None)

    return {
        "success": outcome == "open",
        "roll": roll,
        "total": total,
        "dc": dc,
        "window_low": window_low,
        "window_high": window_high,
        "outcome": outcome,
        "description": desc,
    }


# ── Gamble ──────────────────────────────────────────────────────────────────

def _get_gold(state: dict[str, Any]) -> int:
    """Get gold from either nested player or top-level state."""
    if "player" in state and isinstance(state["player"], dict):
        return state["player"].get("gold", 0)
    return state.get("gold", 0)


def _set_gold(state: dict[str, Any], amount: int) -> None:
    """Set gold on both nested player and top-level state for compatibility."""
    if "player" in state and isinstance(state["player"], dict):
        state["player"]["gold"] = amount
    state["gold"] = amount


def resolve_gamble(state: dict[str, Any], amount: int, rng: Any = None) -> dict:
    """Bet gold, d20 vs opponent, higher wins.

    On tie: player wins (house advantage reversal — adventurer luck).
    Returns result dict with keys: success, player_roll, opponent_roll,
    amount, payout, description.
    """
    _rng = rng or random.Random()

    gold = _get_gold(state)

    if amount <= 0:
        return {"success": False, "reason": "Must bet a positive amount.", "amount": amount}

    if gold < amount:
        return {"success": False, "reason": f"Not enough gold. You have {gold}, need {amount}.", "amount": amount}

    player_roll = _rng.randint(1, 20)
    opponent_roll = _rng.randint(1, 20)

    # CHA modifier gives a slight edge
    player_stats = state.get("player", {}).get("stats")
    stats = player_stats if player_stats else state.get("stats", {})
    cha_mod = get_stat_modifier(stats.get("CHA", 10))
    player_roll += cha_mod

    won = player_roll >= opponent_roll

    if won:
        payout = amount
        _set_gold(state, gold + payout)
        desc = f"You win! ({player_roll} vs {opponent_roll}). +{payout} gold."
    else:
        payout = -amount
        _set_gold(state, max(0, gold - amount))
        desc = f"You lose! ({player_roll} vs {opponent_roll}). -{amount} gold."

    return {
        "success": won,
        "player_roll": player_roll,
        "opponent_roll": opponent_roll,
        "amount": amount,
        "payout": payout,
        "gold_remaining": _get_gold(state),
        "description": desc,
    }


# ── Snapshot / Abort ────────────────────────────────────────────────────────

def get_minigame_snapshot(state: dict[str, Any]) -> dict:
    """Return the current minigame state for layout JSON rendering."""
    mg = state.get("minigame", {})
    return {
        "active": mg.get("active", False),
        "type": mg.get("type", ""),
        "lock_dc": mg.get("lock_dc", 0),
        "bet_amount": mg.get("bet_amount", 0),
        "description": mg.get("description", ""),
    }


def abort_minigame(state: dict[str, Any]) -> dict:
    """Cancel the current minigame and clean up state."""
    mg = state.pop("minigame", None)
    if mg is None:
        return {"aborted": False, "reason": "No active minigame."}
    return {
        "aborted": True,
        "type": mg.get("type", ""),
        "description": f"Minigame '{mg.get('type', 'unknown')}' aborted.",
    }
