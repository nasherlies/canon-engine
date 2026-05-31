"""Reusable text prompts for Canon Engine.

Provides Rich-powered interactive prompts for character creation, world
selection, backstory selection, and other setup flows.  Each prompt function
returns a dict of the player's choices that can be merged into game state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.text import Text
from rich.table import Table
from rich.rule import Rule

console = Console()

# ── Path helpers ─────────────────────────────────────────────────────────────

_CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "content"
_PRESETS_DIR = _CONTENT_DIR / "presets"


def _load_json(filename: str, directory: Path | None = None) -> Any:
    """Load a JSON file from *directory* (defaults to _CONTENT_DIR)."""
    d = directory or _CONTENT_DIR
    path = d / filename
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


# ── Colour palette ───────────────────────────────────────────────────────────
_RARITY_COLORS = {
    "common": "dim white",
    "uncommon": "green",
    "rare": "blue",
    "epic": "magenta",
    "legendary": "yellow",
    "mythical": "red",
}


# ── World / Genre selection ──────────────────────────────────────────────────

def prompt_world_selection() -> Dict[str, Any]:
    """Present available world/genre presets and return the chosen one.

    Returns
    -------
    dict
        The selected world preset dict (from ``content/presets/worlds.json``).
    """
    worlds = _load_json("worlds.json", _PRESETS_DIR)
    if not worlds:
        console.print("[yellow]No world presets found. Using defaults.[/yellow]")
        return {"id": "medieval_fantasy", "name": "Medieval Fantasy", "genre": "fantasy"}

    console.print(Rule(title="[bold magenta]Choose Your World[/bold magenta]"))

    table = Table(show_header=True, header_style="bold cyan", show_lines=True)
    table.add_column("#", style="bold white", width=3)
    table.add_column("World", style="bold yellow")
    table.add_column("Genre", style="green")
    table.add_column("Description", style="dim white")

    world_list = list(worlds.values()) if isinstance(worlds, dict) else worlds
    for i, w in enumerate(world_list, 1):
        table.add_row(
            str(i),
            w.get("name", "Unknown"),
            w.get("genre", "—"),
            w.get("description", "")[:80],
        )

    console.print(table)
    console.print()

    choice = IntPrompt.ask(
        "[bold cyan]Select world number[/bold cyan]",
        default=1,
    )
    idx = max(1, min(choice, len(world_list))) - 1
    selected = world_list[idx]
    console.print(f"\n[green]✓ Selected: {selected.get('name', 'Unknown')}[/green]\n")
    return selected


# ── Character selection ──────────────────────────────────────────────────────

def prompt_character_selection() -> Dict[str, Any]:
    """Present preset characters and let the player pick one or create custom.

    Returns
    -------
    dict
        The selected or custom character dict.
    """
    characters = _load_json("characters.json", _PRESETS_DIR)
    if not characters:
        console.print("[yellow]No character presets found. Creating custom.[/yellow]")
        return prompt_character_creation()

    console.print(Rule(title="[bold magenta]Choose Your Character[/bold magenta]"))

    char_list = list(characters.values()) if isinstance(characters, dict) else characters

    table = Table(show_header=True, header_style="bold cyan", show_lines=True)
    table.add_column("#", style="bold white", width=3)
    table.add_column("Name", style="bold yellow")
    table.add_column("Archetype", style="green")
    table.add_column("STR", justify="right")
    table.add_column("DEX", justify="right")
    table.add_column("INT", justify="right")
    table.add_column("CHA", justify="right")
    table.add_column("CON", justify="right")
    table.add_column("LCK", justify="right")

    for i, c in enumerate(char_list, 1):
        stats = c.get("stats", {})
        table.add_row(
            str(i),
            c.get("name", "Unknown"),
            c.get("archetype", "—"),
            str(stats.get("STR", 10)),
            str(stats.get("DEX", 10)),
            str(stats.get("INT", 10)),
            str(stats.get("CHA", 10)),
            str(stats.get("CON", 10)),
            str(stats.get("LCK", 10)),
        )

    table.add_row(
        str(len(char_list) + 1),
        "[italic]Custom Character[/italic]",
        "—", "—", "—", "—", "—", "—", "—",
    )

    console.print(table)
    console.print()

    choice = IntPrompt.ask(
        "[bold cyan]Select character number[/bold cyan]",
        default=1,
    )

    if choice == len(char_list) + 1:
        return prompt_character_creation()

    idx = max(1, min(choice, len(char_list))) - 1
    selected = char_list[idx]
    console.print(f"\n[green]✓ Selected: {selected.get('name', 'Unknown')}[/green]\n")
    return selected


# ── Custom character creation ────────────────────────────────────────────────

def prompt_character_creation() -> Dict[str, Any]:
    """Walk the player through creating a custom character.

    Returns
    -------
    dict
        A character dict with keys: name, stats, archetype, speech_style,
        backstory.
    """
    console.print(Rule(title="[bold magenta]Create Your Character[/bold magenta]"))
    console.print()

    name = Prompt.ask("[cyan]Character name[/cyan]", default="Adventurer")

    # Archetype
    archetypes = ["knight", "rogue", "mage", "ranger", "cleric", "bard", "barbarian"]
    console.print(f"[cyan]Archetypes:[/cyan] {', '.join(archetypes)}")
    archetype = Prompt.ask("[cyan]Archetype[/cyan]", default="knight").lower()
    if archetype not in archetypes:
        console.print(f"[dim]Unknown archetype '{archetype}', defaulting to 'knight'.[/dim]")
        archetype = "knight"

    # Stats
    console.print()
    console.print("[cyan]Distribute 80 stat points among STR, DEX, INT, CHA, CON, LCK.[/cyan]")
    console.print("[dim]Each stat starts at 8.  Enter values that sum to 80.[/dim]")
    console.print()

    default_stats = {"STR": 13, "DEX": 12, "INT": 12, "CHA": 12, "CON": 12, "LCK": 9}
    stats: Dict[str, int] = {}
    total = 0

    for stat_name in ["STR", "DEX", "INT", "CHA", "CON", "LCK"]:
        remaining = 80 - total
        remaining_for_rest = 6 - len(stats)
        default_val = max(8, remaining // max(remaining_for_rest, 1))
        val = IntPrompt.ask(
            f"  [yellow]{stat_name}[/yellow] (remaining pool: {remaining})",
            default=default_stats.get(stat_name, default_val),
        )
        val = max(1, val)
        stats[stat_name] = val
        total += val

    if total != 80:
        console.print(f"[yellow]⚠ Stats sum to {total}, adjusting LCK to balance.[/yellow]")
        diff = 80 - total
        stats["LCK"] = max(1, stats["LCK"] + diff)

    # Speech style
    speech_style = Prompt.ask(
        "[cyan]Speech style[/cyan] (e.g. 'formal', 'western_drawl', 'pirate', 'default')",
        default="default",
    )

    # Backstory
    backstory = prompt_backstory_selection(archetype)

    console.print()
    console.print(f"[green]✓ Character '{name}' the {archetype} created![/green]\n")

    return {
        "name": name,
        "stats": stats,
        "archetype": archetype,
        "speech_style": speech_style,
        "backstory": backstory,
    }


# ── Backstory selection ──────────────────────────────────────────────────────

def prompt_backstory_selection(archetype: str = "knight") -> str:
    """Present backstory options and return the chosen backstory text.

    Parameters
    ----------
    archetype : str
        The character archetype to filter backstories for.

    Returns
    -------
    str
        The backstory text.
    """
    backstories = _load_json("backstories.json", _PRESETS_DIR)
    if not backstories:
        return _prompt_custom_backstory()

    # Try archetype-specific, then fallback to any
    options = backstories.get(archetype, backstories.get("default", []))
    if not options:
        # Try flat list
        if isinstance(backstories, list):
            options = backstories
        else:
            options = []

    if not options:
        return _prompt_custom_backstory()

    console.print(Rule(title="[bold magenta]Choose Your Backstory[/bold magenta]"))

    table = Table(show_header=True, header_style="bold cyan", show_lines=True)
    table.add_column("#", style="bold white", width=3)
    table.add_column("Title", style="bold yellow")
    table.add_column("Preview", style="dim white")

    for i, b in enumerate(options, 1):
        if isinstance(b, dict):
            table.add_row(str(i), b.get("title", "—"), b.get("text", "")[:80] + "…")
        else:
            table.add_row(str(i), "—", str(b)[:80] + "…")

    table.add_row(str(len(options) + 1), "[italic]Write your own[/italic]", "—")
    console.print(table)
    console.print()

    choice = IntPrompt.ask("[cyan]Select backstory number[/cyan]", default=1)

    if choice == len(options) + 1:
        return _prompt_custom_backstory()

    idx = max(1, min(choice, len(options))) - 1
    selected = options[idx]
    if isinstance(selected, dict):
        return selected.get("text", selected.get("title", ""))
    return str(selected)


def _prompt_custom_backstory() -> str:
    """Prompt the player to write a custom backstory."""
    console.print("[cyan]Write your character's backstory (end with an empty line):[/cyan]")
    lines: list[str] = []
    while True:
        line = Prompt.ask("", default="")
        if not line:
            break
        lines.append(line)
    return "\n".join(lines) if lines else "A wanderer with no known past."


# ── Starting location selection ──────────────────────────────────────────────

def prompt_location_selection() -> Dict[str, Any]:
    """Present starting locations and return the chosen one.

    Returns
    -------
    dict
        The selected location dict.
    """
    locations = _load_json("locations.json", _PRESETS_DIR)
    if not locations:
        return {"id": "tavern", "name": "The Rusty Tankard", "description": "A dim, smoky tavern."}

    loc_list = list(locations.values()) if isinstance(locations, dict) else locations

    console.print(Rule(title="[bold magenta]Choose Starting Location[/bold magenta]"))

    table = Table(show_header=True, header_style="bold cyan", show_lines=True)
    table.add_column("#", style="bold white", width=3)
    table.add_column("Location", style="bold yellow")
    table.add_column("Description", style="dim white")

    for i, loc in enumerate(loc_list, 1):
        table.add_row(
            str(i),
            loc.get("name", loc.get("id", "Unknown")),
            loc.get("description", "")[:80],
        )

    console.print(table)
    console.print()

    choice = IntPrompt.ask("[cyan]Select location number[/cyan]", default=1)
    idx = max(1, min(choice, len(loc_list))) - 1
    selected = loc_list[idx]
    console.print(f"\n[green]✓ Starting at: {selected.get('name', 'Unknown')}[/green]\n")
    return selected


# ── Full setup flow ──────────────────────────────────────────────────────────

def run_full_setup() -> Dict[str, Any]:
    """Run the complete setup flow: world → character → location.

    Returns
    -------
    dict
        Combined setup result with keys: world, character, location.
    """
    console.print()
    console.print(Panel(
        "[bold yellow]Welcome, adventurer. Let us forge your tale.[/bold yellow]",
        border_style="yellow",
    ))
    console.print()

    world = prompt_world_selection()
    character = prompt_character_selection()
    location = prompt_location_selection()

    return {
        "world": world,
        "character": character,
        "location": location,
    }
