"""Canon Engine — Admin Commands

Password-protected admin commands for game masters / developers.
Compares against CANON_ADMIN_PASSWORD environment variable.

Public API:
    check_admin_password(password) -> bool
    resolve_admin_command(state, cmd_text) -> dict
"""

from __future__ import annotations

import os
from typing import Any


def check_admin_password(password: str) -> bool:
    """Compare the provided password against CANON_ADMIN_PASSWORD env var.

    Returns False if the env var is not set or the password doesn't match.
    """
    expected = os.getenv("CANON_ADMIN_PASSWORD", "")
    if not expected:
        return False
    return password == expected


def resolve_admin_command(state: dict[str, Any], cmd_text: str) -> dict:
    """Execute an admin command.

    Supported commands:
        /admin heal          — Restore player to full HP/MP/STM
        /admin gold <amount> — Set player gold to amount
        /admin xp <amount>   — Grant XP
        /admin level <n>     — Set player level
        /admin tp <location> — Teleport to location
        /admin kill          — Kill all enemies in combat
        /admin status        — Show admin status info
        /admin unlock <quest>— Force-complete a quest

    Parameters
    ----------
    state : dict
        Mutable game state.
    cmd_text : str
        The full admin command text (e.g. "/admin heal").

    Returns
    -------
    dict
        Result with keys: success, command, description, and command-specific data.
    """
    parts = cmd_text.strip().split(None, 2)
    # Strip /admin prefix
    if parts and parts[0].lower() == "/admin":
        parts = parts[1:]

    if not parts:
        return {
            "success": False,
            "command": "admin",
            "description": "No admin subcommand. Available: heal, gold, xp, level, tp, kill, status, unlock",
        }

    subcmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    # ── heal ─────────────────────────────────────────────────────────────
    if subcmd == "heal":
        player = state.get("player", state)
        hp_max = player.get("hp_max", player.get("max_hp", 100))
        mp_max = player.get("mp_max", 50)
        stm_max = player.get("stm_max", 100)

        player["hp"] = hp_max
        state["hp"] = hp_max
        player["mp"] = mp_max
        player["stm"] = stm_max

        # Clear negative statuses
        statuses = player.get("statuses", [])
        player["statuses"] = [
            s for s in statuses
            if isinstance(s, dict) and s.get("id") not in ("poison", "bleed", "burn", "stun")
        ]

        return {
            "success": True,
            "command": "heal",
            "description": f"Player healed to full. HP={hp_max}, MP={mp_max}, STM={stm_max}",
        }

    # ── gold ─────────────────────────────────────────────────────────────
    elif subcmd == "gold":
        try:
            amount = int(args)
        except (ValueError, IndexError):
            return {"success": False, "command": "gold", "description": "Usage: /admin gold <amount>"}

        player = state.get("player", state)
        player["gold"] = amount
        state["gold"] = amount

        return {
            "success": True,
            "command": "gold",
            "description": f"Gold set to {amount}",
            "gold": amount,
        }

    # ── xp ───────────────────────────────────────────────────────────────
    elif subcmd == "xp":
        try:
            amount = int(args)
        except (ValueError, IndexError):
            return {"success": False, "command": "xp", "description": "Usage: /admin xp <amount>"}

        player = state.get("player", state)
        player["xp"] = player.get("xp", 0) + amount
        state["xp"] = player.get("xp", 0)

        return {
            "success": True,
            "command": "xp",
            "description": f"Granted {amount} XP. Total: {player['xp']}",
            "xp_total": player["xp"],
        }

    # ── level ────────────────────────────────────────────────────────────
    elif subcmd == "level":
        try:
            level = int(args)
        except (ValueError, IndexError):
            return {"success": False, "command": "level", "description": "Usage: /admin level <n>"}

        player = state.get("player", state)
        player["level"] = level
        state["level"] = level

        return {
            "success": True,
            "command": "level",
            "description": f"Level set to {level}",
            "level": level,
        }

    # ── tp (teleport) ────────────────────────────────────────────────────
    elif subcmd == "tp":
        location = args.strip()
        if not location:
            return {"success": False, "command": "tp", "description": "Usage: /admin tp <location>"}

        world = state.setdefault("world", {})
        world["location"] = location

        return {
            "success": True,
            "command": "tp",
            "description": f"Teleported to {location}",
            "location": location,
        }

    # ── kill ─────────────────────────────────────────────────────────────
    elif subcmd == "kill":
        combat = state.get("combat", {})
        if not combat.get("active", False):
            return {"success": False, "command": "kill", "description": "No active combat."}

        enemies = combat.get("enemies", [])
        for e in enemies:
            e["hp"] = 0
            e["alive"] = False

        return {
            "success": True,
            "command": "kill",
            "description": f"All {len(enemies)} enemies defeated.",
            "enemies_killed": len(enemies),
        }

    # ── status ───────────────────────────────────────────────────────────
    elif subcmd == "status":
        player = state.get("player", state)
        return {
            "success": True,
            "command": "status",
            "description": "Admin status report",
            "hp": player.get("hp", 0),
            "hp_max": player.get("hp_max", player.get("max_hp", 100)),
            "gold": player.get("gold", 0),
            "level": player.get("level", state.get("level", 1)),
            "xp": player.get("xp", 0),
            "location": state.get("world", {}).get("location", "Unknown"),
            "turn": state.get("turn", 0),
            "combat_active": state.get("combat", {}).get("active", False),
            "tutorial_active": state.get("tutorial", {}).get("active", False),
        }

    # ── unlock ───────────────────────────────────────────────────────────
    elif subcmd == "unlock":
        quest_id = args.strip()
        if not quest_id:
            return {"success": False, "command": "unlock", "description": "Usage: /admin unlock <quest_id>"}

        quests = state.setdefault("world", {}).setdefault("quests", {})
        active = quests.setdefault("active", {})
        completed = quests.setdefault("completed", {})

        if quest_id in active:
            quest_data = active.pop(quest_id)
            completed[quest_id] = quest_data
            return {
                "success": True,
                "command": "unlock",
                "description": f"Quest '{quest_id}' force-completed.",
            }

        return {
            "success": False,
            "command": "unlock",
            "description": f"Quest '{quest_id}' not found in active quests.",
        }

    # ── unknown ──────────────────────────────────────────────────────────
    else:
        return {
            "success": False,
            "command": subcmd,
            "description": f"Unknown admin command: '{subcmd}'. Available: heal, gold, xp, level, tp, kill, status, unlock",
        }
