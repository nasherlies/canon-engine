"""
Canon Engine — Command Parser

Parses player input into (kind, args_dict) tuples.
Bare text (no leading /) becomes kind='say' with args={'words': text}.
Empty input returns kind='error'.
"""

from __future__ import annotations

import shlex
import re

# ---------------------------------------------------------------------------
# Command registry: maps slash-command name → (kind, arg_extractor)
#
# arg_extractor is a callable that receives the *remaining text* after the
# command name and returns a dict of parsed arguments.
# ---------------------------------------------------------------------------

def _extract_words(rest: str) -> dict:
    """Return {'words': rest.strip()}."""
    return {"words": rest.strip()}


def _extract_none(rest: str) -> dict:
    """No arguments."""
    return {}


def _extract_item(rest: str) -> dict:
    """Single-item argument."""
    return {"item": rest.strip()}


def _extract_target(rest: str) -> dict:
    """Single-target argument."""
    return {"target": rest.strip()}


def _extract_name(rest: str) -> dict:
    return {"name": rest.strip()}


def _extract_stat(rest: str) -> dict:
    return {"stat": rest.strip()}


def _extract_skill_id(rest: str) -> dict:
    return {"skill_id": rest.strip()}


def _extract_id(rest: str) -> dict:
    return {"id": rest.strip()}


def _extract_slot(rest: str) -> dict:
    return {"slot": rest.strip()}


def _extract_destination(rest: str) -> dict:
    return {"destination": rest.strip()}


def _extract_topic(rest: str) -> dict:
    return {"topic": rest.strip()}


def _extract_npc(rest: str) -> dict:
    return {"npc": rest.strip()}


def _extract_amount(rest: str) -> dict:
    return {"amount": rest.strip()}


def _extract_cmd(rest: str) -> dict:
    return {"cmd": rest.strip()}


def _extract_text(rest: str) -> dict:
    return {"text": rest.strip()}


def _extract_combine(rest: str) -> dict:
    """Parse '/combine <item1> and <item2>'."""
    match = re.match(r"(.+?)\s+and\s+(.+)", rest.strip(), re.IGNORECASE)
    if match:
        return {"item1": match.group(1).strip(), "item2": match.group(2).strip()}
    return {"item1": rest.strip(), "item2": ""}


def _extract_give(rest: str) -> dict:
    """Parse '/give <item> to <recipient>'."""
    match = re.match(r"(.+?)\s+to\s+(.+)", rest.strip(), re.IGNORECASE)
    if match:
        return {"item": match.group(1).strip(), "recipient": match.group(2).strip()}
    return {"item": rest.strip(), "recipient": ""}


def _extract_gift(rest: str) -> dict:
    """Parse '/gift <item> to <npc>'."""
    match = re.match(r"(.+?)\s+to\s+(.+)", rest.strip(), re.IGNORECASE)
    if match:
        return {"item": match.group(1).strip(), "npc": match.group(2).strip()}
    return {"item": rest.strip(), "npc": ""}


def _extract_order(rest: str) -> dict:
    """Parse '/order <companion> <action>'."""
    parts = rest.strip().split(None, 1)
    companion = parts[0] if parts else ""
    action = parts[1] if len(parts) > 1 else ""
    return {"companion": companion, "action": action}


def _extract_craft(rest: str) -> dict:
    """Parse '/craft list' or '/craft <id>'."""
    arg = rest.strip()
    if arg.lower() == "list":
        return {"id": "list"}
    return {"id": arg}


def _extract_look_enemies(rest: str) -> dict:
    """Already matched as /look enemies."""
    return {}


def _extract_help(rest: str) -> dict:
    topic = rest.strip()
    return {"topic": topic} if topic else {}


def _extract_collide(rest: str) -> dict:
    """Parse '/collide <genre1> <genre2>'."""
    parts = rest.strip().split(None, 1)
    genre1 = parts[0] if parts else ""
    genre2 = parts[1] if len(parts) > 1 else ""
    return {"genre1": genre1, "genre2": genre2}


# ---------------------------------------------------------------------------
# Zero-argument commands (no arguments expected)
# ---------------------------------------------------------------------------
_NO_ARG_COMMANDS: dict[str, str] = {
    "look": "look",
    "inv": "inv",
    "inventory": "inv",
    "block": "block",
    "flee": "flee",
    "fight": "fight",
    "turn": "turn",
    "quicksave": "quicksave",
    "menu": "menu",
    "quit": "quit",
    "start_character": "start_character",
    "stats": "stats",
    "levelup": "levelup",
    "skills": "skills",
    "factions": "factions",
    "reputation": "reputation",
    "shop": "shop",
    "barter": "barter",
    "rent": "rent",
    "scavenge": "scavenge",
    "nap": "nap",
    "sleep": "sleep",
    "scout": "scout",
    "stealth": "stealth",
    "cover": "cover",
    "climb": "climb",
    "map": "map",
    "world": "world",
    "quests": "quests",
    "npcs": "npcs",
    "soul": "soul",
    "anchor": "anchor",
    "lockpick": "lockpick",
    "encounter": "encounter",
    "choices": "choices",
    "summary": "summary",
}

# ---------------------------------------------------------------------------
# Commands with arguments — maps command name → (kind, extractor)
# ---------------------------------------------------------------------------
_ARG_COMMANDS: dict[str, tuple[str, callable]] = {
    "say": ("say", _extract_words),
    "do": ("do", _extract_words),
    "think": ("think", _extract_words),
    "talk": ("talk", _extract_words),
    "inspect": ("inspect", _extract_item),
    "use": ("use", _extract_item),
    "equip": ("equip", _extract_item),
    "drop": ("drop", _extract_item),
    "attack": ("attack", _extract_target),
    "item": ("item", _extract_name),
    "combine": ("combine", _extract_combine),
    "give": ("give", _extract_give),
    "save": ("save", _extract_slot),
    "load": ("load", _extract_slot),
    "help": ("help", _extract_help),
    "addstat": ("addstat", _extract_stat),
    "unlock": ("unlock", _extract_skill_id),
    "craft": ("craft", _extract_craft),
    "buy": ("buy", _extract_item),
    "sell": ("sell", _extract_item),
    "travel": ("travel", _extract_destination),
    "interact": ("interact", _extract_target),
    "lore": ("lore", _extract_topic),
    "quest": ("quest", _extract_id),
    "accept": ("accept", _extract_id),
    "abandon": ("abandon", _extract_id),
    "turnin": ("turnin", _extract_id),
    "npc": ("npc", _extract_id),
    "gift": ("gift", _extract_gift),
    "threaten": ("threaten", _extract_npc),
    "recruit": ("recruit", _extract_npc),
    "dismiss": ("dismiss", _extract_npc),
    "companion": ("companion", _extract_npc),
    "order": ("order", _extract_order),
    "remember": ("remember", _extract_text),
    "bribe": ("bribe", _extract_npc),
    "gamble": ("gamble", _extract_amount),
    "admin": ("admin", _extract_cmd),
    "retcon": ("retcon", _extract_text),
    "collide": ("collide", _extract_collide),
    "author": ("author", _extract_text),
}

# Special case: /look enemies
_LOOK_ENEMIES_RE = re.compile(r"^look\s+enemies$", re.IGNORECASE)


def parse_command(text: str) -> tuple[str, dict]:
    """
    Parse player input into a (kind, args) tuple.

    Parameters
    ----------
    text : str
        Raw player input.

    Returns
    -------
    tuple[str, dict]
        (kind, args_dict) — e.g. ('say', {'words': 'hello'}).
        Empty / whitespace-only input → ('error', {}).
        Unknown /command → ('unknown', {'raw': text}).
    """
    if not text or not text.strip():
        return ("error", {})

    stripped = text.strip()

    # --- Bare text (no leading slash) → say ---
    if not stripped.startswith("/"):
        return ("say", {"words": stripped})

    # --- Slash command ---
    # Split into command name and rest on the first whitespace boundary.
    # We manually split to preserve multi-whitespace in args.
    without_slash = stripped[1:]  # drop leading /
    # Split on first whitespace to get command name
    match = re.match(r"(\S+)\s*(.*)", without_slash, re.DOTALL)
    if not match:
        # Input was just "/"
        return ("unknown", {"raw": stripped})

    cmd_name = match.group(1).lower()
    rest = match.group(2).strip()

    # Special handling: /look enemies
    if cmd_name == "look" and rest.lower() == "enemies":
        return ("look_enemies", {})

    # Zero-arg commands
    if cmd_name in _NO_ARG_COMMANDS:
        return (_NO_ARG_COMMANDS[cmd_name], {})

    # Commands with arguments
    if cmd_name in _ARG_COMMANDS:
        kind, extractor = _ARG_COMMANDS[cmd_name]
        return (kind, extractor(rest))

    # Unknown command
    return ("unknown", {"raw": stripped})
