"""
Canon Engine — Command Parser
==============================

The front desk of the engine.  Every line the player types enters here and
exits as a structured ``dict`` (a *parse result*) with at least a ``kind``
key identifying the command verb and any extracted arguments.

Design principles
-----------------
* **Slash-first** — every interaction is a ``/command``.  Plain text is
  silently promoted to ``/say …``.
* **Case-insensitive heads** — ``/Say``, ``/SAY``, ``/say`` all resolve to
  the same handler.
* **Zero external deps** — pure stdlib so the parser can ship as a single
  file inside lightweight clients.
* **Forward-compatible** — unknown ``/commands`` still produce a dict with
  ``kind`` set; the router decides what to do with them.

Public API
----------
* ``parse_command(line: str) -> dict`` — the single entry point.
* ``CommandError`` — raised for malformed input (optional, currently unused;
  callers may prefer the ``_error`` dict convention).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Every recognised command head (lower-case, no leading slash).
COMMAND_HEADS: frozenset[str] = frozenset({
    # Core dialogue / action
    "say", "do", "look", "move",
    # Combat
    "attack", "fight", "flee", "block",
    # Inventory / gear
    "inv", "inventory", "use", "equip", "item", "inspect", "drop",
    "combine", "give",
    # Character / progression
    "stats", "companions", "skills", "unlock", "levelup", "addstat",
    # World knowledge
    "lore", "world", "map", "travel",
    # NPC / faction
    "talk", "shop", "buy", "sell", "barter",
    "scavenge", "rent",
    "npcs", "npc", "gift", "threaten",
    "factions", "reputation",
    # Quests
    "quests", "quest", "accept", "abandon", "turnin",
    # Save / load
    "save", "load", "quicksave",
    # Rest
    "nap", "sleep",
    # Stealth / traps
    "scout", "stealth", "detect", "disarm",
    # Crafting
    "craft",
    # Soul / underworld
    "soul", "remember", "anchor", "bribe",
    "ascend", "descend", "underworld",
    "death_continue", "death_yield",
    "rebirth",
    # Order (companion)
    "order",
    # Help / UI
    "help", "menu", "quit", "exit", "back",
    # Tutorial
    "tutorial",
    # Admin / dev
    "admin", "edit", "spawn", "retcon",
    "author", "summary", "encounter", "choices", "consequences", "collide",
    "model", "verbose", "lang",
    "dump", "godmode", "setseed",
    "start_character",
})

# Valid stat names for ``/addstat``
_VALID_STATS = {"STR", "DEX", "INT", "CHA", "CON", "LCK"}

# Valid rebirth paths
_VALID_REBIRTH_PATHS = {
    "standard", "permanent", "ascension", "descension", "purgatory_negotiated",
}

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CommandError(Exception):
    """Raised when a raw input line cannot be turned into a command dict."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

#: Matches an optional leading slash on a command head.
_SLASH_RE = re.compile(r"^/(\S+)")


def _split_head_rest(line: str) -> tuple[str, str]:
    """Return ``(head, rest)`` where *head* is the first token (lowered,
    slash stripped) and *rest* is everything after it, trimmed.

    If the line has no slash prefix, the whole line is treated as *rest*
    with an implicit ``say`` head.
    """
    stripped = line.strip()
    m = _SLASH_RE.match(stripped)
    if m:
        head = m.group(1).lower()
        rest = stripped[m.end():].strip()
        return head, rest
    # No slash → implicit /say
    return "say", stripped


def _build(kind: str, **kwargs: Any) -> dict[str, Any]:
    """Shorthand to build a parse-result dict."""
    d: dict[str, Any] = {"kind": kind}
    d.update(kwargs)
    return d


def _error(msg: str) -> dict[str, Any]:
    """Return an error-flavoured parse result instead of raising."""
    return {"kind": "error", "error": msg}


# ---------------------------------------------------------------------------
# Per-command parsers
# ---------------------------------------------------------------------------

def _parse_say(rest: str) -> dict[str, Any]:
    """/say <text> — Speak dialogue."""
    return _build("say", text=rest)


def _parse_do(rest: str) -> dict[str, Any]:
    """/do <action> — Perform an action."""
    return _build("do", text=rest)


def _parse_look(rest: str) -> dict[str, Any]:
    """/look [target] — Examine surroundings or an object."""
    return _build("look", target=rest or None)


def _parse_move(rest: str) -> dict[str, Any]:
    """/move <direction|place> — Travel in a direction."""
    return _build("move", direction=rest)


def _parse_attack(rest: str) -> dict[str, Any]:
    """/attack <target> or /attack <n> — Combat action."""
    return _build("attack", target=rest)


def _parse_use(rest: str) -> dict[str, Any]:
    """/use <item> — Use an inventory item."""
    return _build("use", item=rest)


def _parse_equip(rest: str) -> dict[str, Any]:
    """/equip <item> — Equip gear."""
    return _build("equip", item=rest)


def _parse_inv(_rest: str) -> dict[str, Any]:
    """/inv or /inventory — Open inventory."""
    return _build("inv")


def _parse_stats(_rest: str) -> dict[str, Any]:
    """/stats — View character sheet."""
    return _build("stats")


def _parse_companions(_rest: str) -> dict[str, Any]:
    """/companions — View followers."""
    return _build("companions")


def _parse_lore(rest: str) -> dict[str, Any]:
    """/lore [topic] — Query world bible."""
    return _build("lore", topic=rest or None)


def _parse_save(rest: str) -> dict[str, Any]:
    """/save [slotname] — Save game."""
    return _build("save", slot=rest or None)


def _parse_load(rest: str) -> dict[str, Any]:
    """/load [slotname] — Load game."""
    return _build("load", slot=rest or None)


def _parse_quicksave(_rest: str) -> dict[str, Any]:
    """/quicksave — Quick-save."""
    return _build("quicksave")


def _parse_help(rest: str) -> dict[str, Any]:
    """/help or /help <topic_id> — Command list or handbook page."""
    return _build("help", topic=rest or None)


def _parse_menu(_rest: str) -> dict[str, Any]:
    """/menu or /quit or /exit — End session."""
    return _build("menu")


def _parse_back(_rest: str) -> dict[str, Any]:
    """/back — Close overlay."""
    return _build("back")


def _parse_world(_rest: str) -> dict[str, Any]:
    """/world — World/run sheet."""
    return _build("world")


def _parse_map(_rest: str) -> dict[str, Any]:
    """/map — Map/graph sheet."""
    return _build("map")


def _parse_travel(rest: str) -> dict[str, Any]:
    """/travel <place> — Move along travel graph."""
    return _build("travel", place=rest)


def _parse_talk(_rest: str) -> dict[str, Any]:
    """/talk — Encounter dialogue."""
    return _build("talk")


def _parse_flee(_rest: str) -> dict[str, Any]:
    """/flee — Flee standoff or combat."""
    return _build("flee")


def _parse_fight(_rest: str) -> dict[str, Any]:
    """/fight — Commit to combat."""
    return _build("fight")


def _parse_block(_rest: str) -> dict[str, Any]:
    """/block — Defensive stance."""
    return _build("block")


def _parse_item(rest: str) -> dict[str, Any]:
    """/item <name> — Use consumable in combat."""
    return _build("item", item=rest)


def _parse_order(rest: str) -> dict[str, Any]:
    """/order <name> attack <n> | block | item <item> | flee — Companion orders."""
    return _build("order", raw=rest)


def _parse_shop(_rest: str) -> dict[str, Any]:
    """/shop — List merchant wares."""
    return _build("shop")


def _parse_buy(rest: str) -> dict[str, Any]:
    """/buy <index> — Buy by index."""
    return _build("buy", index=rest)


def _parse_sell(rest: str) -> dict[str, Any]:
    """/sell <item> — Sell item."""
    return _build("sell", item=rest)


def _parse_barter(rest: str) -> dict[str, Any]:
    """/barter <index> — Haggle."""
    return _build("barter", index=rest)


def _parse_scavenge(_rest: str) -> dict[str, Any]:
    """/scavenge — Scavenge roll."""
    return _build("scavenge")


def _parse_rent(_rest: str) -> dict[str, Any]:
    """/rent — Pay for rest."""
    return _build("rent")


def _parse_inspect(rest: str) -> dict[str, Any]:
    """/inspect <item> — Item detail."""
    return _build("inspect", item=rest)


def _parse_drop(rest: str) -> dict[str, Any]:
    """/drop <item> [--confirm] — Drop item."""
    confirm = False
    text = rest
    if rest.endswith("--confirm"):
        confirm = True
        text = rest[: -len("--confirm")].strip()
    return _build("drop", item=text, confirm=confirm)


def _parse_combine(rest: str) -> dict[str, Any]:
    """/combine A and B — Combine items."""
    parts = re.split(r"\s+and\s+", rest, maxsplit=1)
    if len(parts) == 2:
        return _build("combine", item_a=parts[0].strip(), item_b=parts[1].strip())
    return _build("combine", item_a=rest, item_b=None)


def _parse_give(rest: str) -> dict[str, Any]:
    """/give <item> to <target> — Hand item to NPC."""
    m = re.match(r"(.+?)\s+to\s+(.+)", rest)
    if m:
        return _build("give", item=m.group(1).strip(), target=m.group(2).strip())
    return _build("give", item=rest, target=None)


def _parse_craft(rest: str) -> dict[str, Any]:
    """/craft list or /craft <recipe_id> — Crafting."""
    if rest.lower() == "list" or not rest:
        return _build("craft", recipe_id=None, list_recipes=True)
    return _build("craft", recipe_id=rest, list_recipes=False)


def _parse_scout(_rest: str) -> dict[str, Any]:
    """/scout — Scout ahead."""
    return _build("scout")


def _parse_stealth(_rest: str) -> dict[str, Any]:
    """/stealth — Enter stealth."""
    return _build("stealth")


def _parse_detect(_rest: str) -> dict[str, Any]:
    """/detect — Detect traps."""
    return _build("detect")


def _parse_disarm(rest: str) -> dict[str, Any]:
    """/disarm <trap_id> — Disarm a trap."""
    return _build("disarm", trap_id=rest)


def _parse_skills(_rest: str) -> dict[str, Any]:
    """/skills — Show skills."""
    return _build("skills")


def _parse_unlock(rest: str) -> dict[str, Any]:
    """/unlock <skill_id> — Unlock skill."""
    return _build("unlock", skill_id=rest)


def _parse_factions(_rest: str) -> dict[str, Any]:
    """/factions — List factions."""
    return _build("factions")


def _parse_reputation(rest: str) -> dict[str, Any]:
    """/reputation <faction_id> — Faction detail."""
    return _build("reputation", faction_id=rest)


def _parse_npcs(_rest: str) -> dict[str, Any]:
    """/npcs — Who is here."""
    return _build("npcs")


def _parse_npc(rest: str) -> dict[str, Any]:
    """/npc <npc_id> — NPC detail."""
    return _build("npc", npc_id=rest)


def _parse_gift(rest: str) -> dict[str, Any]:
    """/gift <npc_id> <item> — Gift flow."""
    parts = rest.split(None, 1)
    if len(parts) == 2:
        return _build("gift", npc_id=parts[0], item=parts[1])
    return _build("gift", npc_id=parts[0] if parts else None, item=None)


def _parse_threaten(rest: str) -> dict[str, Any]:
    """/threaten <npc_id> — Threaten flow."""
    return _build("threaten", npc_id=rest)


def _parse_quests(_rest: str) -> dict[str, Any]:
    """/quests — List quests."""
    return _build("quests")


def _parse_quest(rest: str) -> dict[str, Any]:
    """/quest <quest_id> — Inspect quest."""
    return _build("quest", quest_id=rest)


def _parse_accept(rest: str) -> dict[str, Any]:
    """/accept <quest_id> — Accept quest."""
    return _build("accept", quest_id=rest)


def _parse_abandon(rest: str) -> dict[str, Any]:
    """/abandon <quest_id> — Drop quest."""
    return _build("abandon", quest_id=rest)


def _parse_turnin(rest: str) -> dict[str, Any]:
    """/turnin <quest_id> — Complete quest."""
    return _build("turnin", quest_id=rest)


def _parse_nap(_rest: str) -> dict[str, Any]:
    """/nap or /sleep — Rest."""
    return _build("nap")


def _parse_levelup(_rest: str) -> dict[str, Any]:
    """/levelup — Level up panel."""
    return _build("levelup")


def _parse_addstat(rest: str) -> dict[str, Any]:
    """/addstat <stat> — Spend stat point."""
    stat = rest.upper()
    if stat not in _VALID_STATS:
        return _error(f"Invalid stat '{rest}'. Valid: {', '.join(sorted(_VALID_STATS))}")
    return _build("addstat", stat=stat)


def _parse_soul(_rest: str) -> dict[str, Any]:
    """/soul — Soul/underworld sheet."""
    return _build("soul")


def _parse_remember(rest: str) -> dict[str, Any]:
    """/remember <memory_id> — Soul memory."""
    return _build("remember", memory_id=rest)


def _parse_anchor(rest: str) -> dict[str, Any]:
    """/anchor <target> — Anchor soul."""
    return _build("anchor", target=rest)


def _parse_bribe(rest: str) -> dict[str, Any]:
    """/bribe <npc_id> — Underworld bribe."""
    return _build("bribe", npc_id=rest)


def _parse_ascend(_rest: str) -> dict[str, Any]:
    """/ascend — Ascend from underworld."""
    return _build("ascend")


def _parse_descend(rest: str) -> dict[str, Any]:
    """/descend or /descend force — Descend to underworld."""
    return _build("descend", force=rest.lower() == "force")


def _parse_underworld(rest: str) -> dict[str, Any]:
    """/underworld enter — Enter underworld."""
    return _build("underworld", action=rest)


def _parse_death_continue(_rest: str) -> dict[str, Any]:
    """/death_continue — Continue after death."""
    return _build("death_continue")


def _parse_death_yield(_rest: str) -> dict[str, Any]:
    """/death_yield — Yield to death."""
    return _build("death_yield")


def _parse_rebirth(rest: str) -> dict[str, Any]:
    """/rebirth <path> — Rebirth path selection."""
    path = rest.lower()
    if path not in _VALID_REBIRTH_PATHS:
        return _error(f"Invalid rebirth path '{rest}'. Valid: {', '.join(sorted(_VALID_REBIRTH_PATHS))}")
    return _build("rebirth", path=path)


def _parse_tutorial(rest: str) -> dict[str, Any]:
    """/tutorial, /tutorial next, /tutorial reset, /tutorial exit."""
    action = rest.lower() if rest else "open"
    return _build("tutorial", action=action)


def _parse_admin(_rest: str) -> dict[str, Any]:
    """/admin — Toggle admin mode."""
    return _build("admin")


def _parse_edit(rest: str) -> dict[str, Any]:
    """/edit <entity> <field> <value> — Modify entity."""
    parts = rest.split(None, 2)
    if len(parts) < 3:
        return _error("/edit requires: <entity> <field> <value>")
    return _build("edit", entity=parts[0], field=parts[1], value=parts[2])


def _parse_spawn(rest: str) -> dict[str, Any]:
    """/spawn <thing> — Force-create."""
    return _build("spawn", thing=rest)


def _parse_retcon(rest: str) -> dict[str, Any]:
    """/retcon <event> — Rewrite past beat."""
    return _build("retcon", event=rest)


def _parse_model(rest: str) -> dict[str, Any]:
    """/model <name> — Hot-swap AI model."""
    return _build("model", name=rest)


def _parse_verbosity(rest: str) -> dict[str, Any]:
    """/verbose <0-3> — Narration depth."""
    try:
        level = int(rest)
    except ValueError:
        return _error("/verbose requires a number 0-3")
    if level not in {0, 1, 2, 3}:
        return _error("/verbose requires a number 0-3")
    return _build("verbose", level=level)


def _parse_lang(rest: str) -> dict[str, Any]:
    """/lang <style> — Force speech style."""
    return _build("lang", style=rest)


def _parse_dump(_rest: str) -> dict[str, Any]:
    """/dump — Print world state."""
    return _build("dump")


def _parse_godmode(_rest: str) -> dict[str, Any]:
    """/godmode — Pump stats (dev only)."""
    return _build("godmode")


def _parse_setseed(rest: str) -> dict[str, Any]:
    """/setseed <text> — Regenerate world (dev only)."""
    return _build("setseed", seed=rest)


def _parse_start_character(_rest: str) -> dict[str, Any]:
    """/start_character — Rebuild session from character dict."""
    return _build("start_character")


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

# Maps each command head (lower-case, no slash) to its parser function.
# Heads that are aliases point to the canonical parser.
_DISPATCH: dict[str, Any] = {
    # Core
    "say": _parse_say,
    "do": _parse_do,
    "look": _parse_look,
    "move": _parse_move,
    # Combat
    "attack": _parse_attack,
    "fight": _parse_fight,
    "flee": _parse_flee,
    "block": _parse_block,
    # Inventory / gear
    "inv": _parse_inv,
    "inventory": _parse_inv,
    "use": _parse_use,
    "equip": _parse_equip,
    "item": _parse_item,
    "inspect": _parse_inspect,
    "drop": _parse_drop,
    "combine": _parse_combine,
    "give": _parse_give,
    # Character
    "stats": _parse_stats,
    "companions": _parse_companions,
    "skills": _parse_skills,
    "unlock": _parse_unlock,
    "levelup": _parse_levelup,
    "addstat": _parse_addstat,
    # World
    "lore": _parse_lore,
    "world": _parse_world,
    "map": _parse_map,
    "travel": _parse_travel,
    # NPC / faction
    "talk": _parse_talk,
    "shop": _parse_shop,
    "buy": _parse_buy,
    "sell": _parse_sell,
    "barter": _parse_barter,
    "scavenge": _parse_scavenge,
    "rent": _parse_rent,
    "npcs": _parse_npcs,
    "npc": _parse_npc,
    "gift": _parse_gift,
    "threaten": _parse_threaten,
    "factions": _parse_factions,
    "reputation": _parse_reputation,
    # Quests
    "quests": _parse_quests,
    "quest": _parse_quest,
    "accept": _parse_accept,
    "abandon": _parse_abandon,
    "turnin": _parse_turnin,
    # Save / load
    "save": _parse_save,
    "load": _parse_load,
    "quicksave": _parse_quicksave,
    # Rest
    "nap": _parse_nap,
    "sleep": _parse_nap,
    # Stealth / traps
    "scout": _parse_scout,
    "stealth": _parse_stealth,
    "detect": _parse_detect,
    "disarm": _parse_disarm,
    # Crafting
    "craft": _parse_craft,
    # Soul / underworld
    "soul": _parse_soul,
    "remember": _parse_remember,
    "anchor": _parse_anchor,
    "bribe": _parse_bribe,
    "ascend": _parse_ascend,
    "descend": _parse_descend,
    "underworld": _parse_underworld,
    "death_continue": _parse_death_continue,
    "death_yield": _parse_death_yield,
    "rebirth": _parse_rebirth,
    # Order
    "order": _parse_order,
    # Help / UI
    "help": _parse_help,
    "menu": _parse_menu,
    "quit": _parse_menu,
    "exit": _parse_menu,
    "back": _parse_back,
    # Tutorial
    "tutorial": _parse_tutorial,
    # Admin / dev
    "admin": _parse_admin,
    "edit": _parse_edit,
    "spawn": _parse_spawn,
    "retcon": _parse_retcon,
    "model": _parse_model,
    "verbose": _parse_verbosity,
    "lang": _parse_lang,
    "dump": _parse_dump,
    "godmode": _parse_godmode,
    "setseed": _parse_setseed,
    "start_character": _parse_start_character,
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def parse_command(line: str) -> dict[str, Any]:
    """Parse a raw player input line into a structured command dict.

    Parameters
    ----------
    line:
        The raw text the player typed.  May or may not start with ``/``.
        If it does not start with ``/``, it is promoted to ``/say …``.

    Returns
    -------
    dict
        Always has at least a ``kind`` key.  Unknown ``/commands`` produce
        ``{"kind": "<head>", "text": "<rest>"}`` so routers can still
        handle them.

    Examples
    --------
    >>> parse_command("Hello there!")
    {'kind': 'say', 'text': 'Hello there!'}
    >>> parse_command("/look sword")
    {'kind': 'look', 'target': 'sword'}
    >>> parse_command("/ATTACK 3")
    {'kind': 'attack', 'target': '3'}
    """
    head, rest = _split_head_rest(line)
    handler = _DISPATCH.get(head)
    if handler is not None:
        return handler(rest)
    # Unknown command — pass through so routers can attempt recovery.
    return _build(head, text=rest)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Quick smoke tests when run directly.
    tests: list[tuple[str, str]] = [
        ("Hello there!", "say"),
        ("/say Hello!", "say"),
        ("/do flips a table", "do"),
        ("/look", "look"),
        ("/look sword", "look"),
        ("/move north", "move"),
        ("/attack 3", "attack"),
        ("/ATTACK goblin", "attack"),
        ("/use potion", "use"),
        ("/equip shield", "equip"),
        ("/inv", "inv"),
        ("/inventory", "inv"),
        ("/stats", "stats"),
        ("/companions", "companions"),
        ("/lore dragons", "lore"),
        ("/save slot1", "save"),
        ("/quicksave", "quicksave"),
        ("/help combat", "help"),
        ("/menu", "menu"),
        ("/quit", "menu"),
        ("/back", "back"),
        ("/world", "world"),
        ("/map", "map"),
        ("/travel village", "travel"),
        ("/talk", "talk"),
        ("/flee", "flee"),
        ("/fight", "fight"),
        ("/block", "block"),
        ("/item potion", "item"),
        ("/look enemies", "look"),
        ("/order alice attack 2", "order"),
        ("/shop", "shop"),
        ("/buy 3", "buy"),
        ("/sell sword", "sell"),
        ("/barter 1", "barter"),
        ("/scavenge", "scavenge"),
        ("/rent", "rent"),
        ("/inspect ring", "inspect"),
        ("/drop rock --confirm", "drop"),
        ("/combine herb and mushroom", "combine"),
        ("/give potion to merchant", "give"),
        ("/craft list", "craft"),
        ("/craft recipe_iron_helm", "craft"),
        ("/scout", "scout"),
        ("/stealth", "stealth"),
        ("/detect", "detect"),
        ("/disarm trap_1", "disarm"),
        ("/skills", "skills"),
        ("/unlock fireball", "unlock"),
        ("/factions", "factions"),
        ("/reputation thieves_guild", "reputation"),
        ("/npcs", "npcs"),
        ("/npc guard_1", "npc"),
        ("/gift alice flowers", "gift"),
        ("/threaten bandit", "threaten"),
        ("/quests", "quests"),
        ("/quest main_01", "quest"),
        ("/accept side_01", "accept"),
        ("/abandon side_01", "abandon"),
        ("/turnin main_01", "turnin"),
        ("/nap", "nap"),
        ("/sleep", "nap"),
        ("/levelup", "levelup"),
        ("/addstat STR", "addstat"),
        ("/addstat str", "addstat"),
        ("/soul", "soul"),
        ("/remember mem_1", "remember"),
        ("/anchor altar", "anchor"),
        ("/bribe ferryman", "bribe"),
        ("/ascend", "ascend"),
        ("/descend", "descend"),
        ("/descend force", "descend"),
        ("/underworld enter", "underworld"),
        ("/death_continue", "death_continue"),
        ("/death_yield", "death_yield"),
        ("/rebirth standard", "rebirth"),
        ("/tutorial", "tutorial"),
        ("/tutorial next", "tutorial"),
        ("/admin", "admin"),
        ("/edit player hp 100", "edit"),
        ("/spawn dragon", "spawn"),
        ("/retcon battle_never_happened", "retcon"),
        ("/model gpt-4", "model"),
        ("/verbose 2", "verbose"),
        ("/lang shakespearean", "lang"),
        ("/dump", "dump"),
        ("/godmode", "godmode"),
        ("/setseed hello_world", "setseed"),
        ("/start_character", "start_character"),
    ]

    passed = 0
    failed = 0
    for raw, expected_kind in tests:
        result = parse_command(raw)
        actual = result.get("kind")
        if actual == expected_kind:
            passed += 1
        else:
            failed += 1
            print(f"FAIL: {raw!r} → expected kind={expected_kind!r}, got {result}")

    print(f"\n{passed}/{passed + failed} tests passed.")
    if failed:
        print(f"{failed} FAILED")
    else:
        print("All tests passed ✓")
