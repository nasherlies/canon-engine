"""Rich terminal layout for Canon Engine.

Renders a multi-panel game view with:
- WORLD VIEW (center) — narrative display
- STATUS PANEL (top) — HP/MP/stamina bars
- COMPANION PANEL (right) — companion info
- INVENTORY PANEL — scrollable list
- COMMAND INPUT + LOG (bottom)

Palette:
    Dirt/Common   → dim white
    Uncommon      → green
    Rare          → blue
    Epic          → magenta
    Legendary     → yellow
    Mythical      → red
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from rich.console import Console, Group
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.rule import Rule
from rich.columns import Columns
from rich.progress_bar import ProgressBar
from rich import box

# ── Colour / rarity palette ──────────────────────────────────────────────────

RARITY_COLORS: Dict[str, str] = {
    "dirt": "dim white",
    "common": "dim white",
    "uncommon": "green",
    "rare": "blue",
    "epic": "magenta",
    "legendary": "yellow",
    "mythical": "red",
}

# Box styles per panel
_STATUS_BOX = box.HEAVY
_NARRATIVE_BOX = box.ROUNDED
_COMPANION_BOX = box.ROUNDED
_INVENTORY_BOX = box.HEAVY
_LOG_BOX = box.ROUNDED

console = Console()


# ── Bar helpers ──────────────────────────────────────────────────────────────

def _make_bar(current: int, maximum: int, width: int = 20, filled_char: str = "█", empty_char: str = "░") -> str:
    """Return a text-based bar like ``████████░░░░░░``."""
    if maximum <= 0:
        return empty_char * width
    ratio = max(0.0, min(1.0, current / maximum))
    filled = int(ratio * width)
    return filled_char * filled + empty_char * (width - filled)


def _bar_color(current: int, maximum: int) -> str:
    """Return a colour based on remaining percentage."""
    if maximum <= 0:
        return "red"
    ratio = current / maximum
    if ratio > 0.6:
        return "green"
    if ratio > 0.3:
        return "yellow"
    return "red"


# ── Status panel ─────────────────────────────────────────────────────────────

def render_status_panel(state: Dict[str, Any]) -> Panel:
    """Render the top status panel with HP, MP, stamina bars."""
    player = state.get("player", {})
    name = player.get("name", "Adventurer")
    level = player.get("level", 1)

    hp = player.get("hp", 100)
    max_hp = player.get("max_hp", 100)
    mp = player.get("mp", 50)
    max_mp = player.get("max_mp", 50)
    stamina = player.get("stamina", 80)
    max_stamina = player.get("max_stamina", 80)

    stats = player.get("stats", {})
    gold = player.get("gold", 0)
    xp = player.get("xp", 0)
    xp_next = player.get("xp_next", 100)

    lines = []
    lines.append(Text(f"  ⚔ {name}  │  Lv.{level}  │  {xp}/{xp_next} XP  │  💰 {gold}g", style="bold white"))
    lines.append(Text(""))
    lines.append(Text(f"  HP  [{_make_bar(hp, max_hp, 20)}]  {hp}/{max_hp}", style=_bar_color(hp, max_hp)))
    lines.append(Text(f"  MP  [{_make_bar(mp, max_mp, 20)}]  {mp}/{max_mp}", style=_bar_color(mp, max_mp)))
    lines.append(Text(f"  STA [{_make_bar(stamina, max_stamina, 20)}]  {stamina}/{max_stamina}", style=_bar_color(stamina, max_stamina)))

    if stats:
        stat_line = "  "
        for s in ["STR", "DEX", "INT", "CHA", "CON", "LCK"]:
            val = stats.get(s, "—")
            stat_line += f"  {s}:{val}"
        lines.append(Text(stat_line, style="dim white"))

    location = state.get("world", {}).get("location_name", "Unknown")
    lines.append(Text(f"  📍 {location}", style="cyan"))

    return Panel(
        Group(*lines),
        title="[bold white]STATUS[/bold white]",
        border_style="white",
        box=_STATUS_BOX,
        padding=(0, 1),
    )


# ── Narrative panel ──────────────────────────────────────────────────────────

def render_narrative_panel(narration: str, max_lines: int = 30) -> Panel:
    """Render the center world-view / narrative panel."""
    text = Text(narration or "The world awaits your command...", style="white")
    return Panel(
        text,
        title="[bold yellow]WORLD VIEW[/bold yellow]",
        border_style="yellow",
        box=_NARRATIVE_BOX,
        padding=(1, 2),
    )


# ── Companion panel ──────────────────────────────────────────────────────────

def render_companion_panel(state: Dict[str, Any]) -> Panel:
    """Render the right-side companion panel."""
    companions = state.get("companions", [])

    if not companions:
        return Panel(
            Text("  No companions yet.", style="dim white"),
            title="[bold green]COMPANIONS[/bold green]",
            border_style="green",
            box=_COMPANION_BOX,
            padding=(0, 1),
        )

    lines = []
    for i, comp in enumerate(companions[:4], 1):
        cname = comp.get("name", "Unknown")
        chp = comp.get("hp", 0)
        cmax = comp.get("max_hp", 0)
        loyalty = comp.get("loyalty", 50)
        archetype = comp.get("archetype", "")

        bar = _make_bar(chp, cmax, 12)
        color = _bar_color(chp, cmax)

        lines.append(Text(f"  {i}. {cname} ({archetype})", style="bold green"))
        lines.append(Text(f"     HP [{bar}] {chp}/{cmax}", style=color))
        lines.append(Text(f"     Loyalty: {loyalty}", style="dim white"))
        lines.append(Text(""))

    return Panel(
        Group(*lines),
        title="[bold green]COMPANIONS[/bold green]",
        border_style="green",
        box=_COMPANION_BOX,
        padding=(0, 1),
    )


# ── Inventory panel ──────────────────────────────────────────────────────────

def render_inventory_panel(state: Dict[str, Any], max_items: int = 15) -> Panel:
    """Render the inventory panel."""
    player = state.get("player", {})
    inventory = player.get("inventory", [])

    if not inventory:
        return Panel(
            Text("  Inventory empty.", style="dim white"),
            title="[bold blue]INVENTORY[/bold blue]",
            border_style="blue",
            box=_INVENTORY_BOX,
            padding=(0, 1),
        )

    table = Table(show_header=True, header_style="bold", show_lines=False, box=None, padding=(0, 1))
    table.add_column("#", style="dim white", width=3)
    table.add_column("Item", style="white")
    table.add_column("Qty", justify="right", style="dim white", width=4)
    table.add_column("Rarity", width=10)

    for i, item in enumerate(inventory[:max_items], 1):
        name = item.get("name", "???") if isinstance(item, dict) else str(item)
        qty = item.get("qty", 1) if isinstance(item, dict) else 1
        rarity = item.get("rarity", "common") if isinstance(item, dict) else "common"
        color = RARITY_COLORS.get(rarity, "dim white")
        table.add_row(str(i), name, str(qty), f"[{color}]{rarity}[/{color}]")

    if len(inventory) > max_items:
        table.add_row("", f"[dim]... and {len(inventory) - max_items} more[/dim]", "", "")

    return Panel(
        table,
        title="[bold blue]INVENTORY[/bold blue]",
        border_style="blue",
        box=_INVENTORY_BOX,
        padding=(0, 1),
    )


# ── Command log panel ────────────────────────────────────────────────────────

def render_log_panel(state: Dict[str, Any], max_entries: int = 5) -> Panel:
    """Render the bottom command log."""
    log = state.get("command_log", [])
    recent = log[-max_entries:]

    if not recent:
        lines = [Text("  No commands yet.", style="dim white")]
    else:
        lines = []
        for entry in recent:
            kind = entry.get("kind", "?") if isinstance(entry, dict) else str(entry)
            lines.append(Text(f"  /{kind}", style="dim cyan"))

    return Panel(
        Group(*lines),
        title="[bold white]COMMAND LOG[/bold white]",
        border_style="dim white",
        box=_LOG_BOX,
        padding=(0, 1),
    )


# ── Full layout ──────────────────────────────────────────────────────────────

def render_full_layout(
    state: Dict[str, Any],
    narration: str = "",
) -> Layout:
    """Compose the full Rich layout from game state.

    Returns a ``rich.layout.Layout`` ready for ``console.print()``.

    Layout::

        ┌──────────── STATUS ─────────────┐
        │                                  │
        ├──────── NARRATIVE ──┬─ COMPANION ─┤
        │                    │             │
        │                    │             │
        ├────────────────────┴─────────────┤
        │           COMMAND LOG            │
        └──────────────────────────────────┘
    """
    layout = Layout()

    layout.split_column(
        Layout(name="status", size=7),
        Layout(name="main"),
        Layout(name="bottom", size=8),
    )

    layout["main"].split_row(
        Layout(name="narrative", ratio=3),
        Layout(name="side", ratio=1),
    )

    layout["side"].split_column(
        Layout(name="companions", ratio=1),
        Layout(name="inventory", ratio=1),
    )

    layout["status"].update(render_status_panel(state))
    layout["narrative"].update(render_narrative_panel(narration))
    layout["companions"].update(render_companion_panel(state))
    layout["inventory"].update(render_inventory_panel(state))
    layout["bottom"].update(render_log_panel(state))

    return layout


# ── Simple text-based layout for API responses ───────────────────────────────

def render_layout_dict(state: Dict[str, Any], narration: str = "") -> Dict[str, Any]:
    """Return a plain dict representation of the layout for API responses.

    This avoids Rich objects and returns JSON-serializable data.
    """
    player = state.get("player", {})
    companions = state.get("companions", [])
    inventory = player.get("inventory", [])
    log = state.get("command_log", [])

    return {
        "status": {
            "name": player.get("name", "Adventurer"),
            "level": player.get("level", 1),
            "hp": player.get("hp", 0),
            "max_hp": player.get("max_hp", 0),
            "mp": player.get("mp", 0),
            "max_mp": player.get("max_mp", 0),
            "stamina": player.get("stamina", 0),
            "max_stamina": player.get("max_stamina", 0),
            "stats": player.get("stats", {}),
            "location": state.get("world", {}).get("location_name", "Unknown"),
        },
        "narrative": narration,
        "companions": [
            {
                "name": c.get("name", "Unknown"),
                "hp": c.get("hp", 0),
                "max_hp": c.get("max_hp", 0),
                "loyalty": c.get("loyalty", 50),
                "archetype": c.get("archetype", ""),
            }
            for c in companions[:4]
        ],
        "inventory": [
            {
                "name": it.get("name", "???") if isinstance(it, dict) else str(it),
                "qty": it.get("qty", 1) if isinstance(it, dict) else 1,
                "rarity": it.get("rarity", "common") if isinstance(it, dict) else "common",
            }
            for it in inventory[:15]
        ],
        "command_log": [e.get("kind", "?") if isinstance(e, dict) else str(e) for e in log[-5:]],
    }


# ── Print to terminal ────────────────────────────────────────────────────────

def print_full_layout(state: Dict[str, Any], narration: str = "") -> None:
    """Render and print the full layout to the terminal."""
    layout = render_full_layout(state, narration)
    console.print(layout)
