"""Start screen menu for Canon Engine.

Displays a Rich-powered title screen with START / SETTINGS / CLOSE options.
Handles configuration tweaks (AI model, API key, verbosity, language style,
autosave interval) before handing off to character selection or the game loop.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.text import Text
from rich.rule import Rule

from canon_engine.constants import ENGINE_NAME, ENGINE_VERSION

console = Console()

# ── Colour palette (matches game_layout.py) ──────────────────────────────────
_PALETTE = {
    "title": "bold yellow",
    "menu_item": "bold cyan",
    "menu_key": "bold white",
    "dim": "dim white",
    "accent": "magenta",
    "success": "green",
    "error": "red",
}

# ── ASCII title banner ───────────────────────────────────────────────────────
_BANNER = r"""
   ╔══════════════════════════════════════════════════════════╗
   ║                                                          ║
   ║       ██████╗ █████╗ ███╗   ██╗ ██████╗ ███╗   ██╗      ║
   ║      ██╔════╝██╔══██╗████╗  ██║██╔═══██╗████╗  ██║      ║
   ║      ██║     ███████║██╔██╗ ██║██║   ██║██╔██╗ ██║      ║
   ║      ██║     ██╔══██║██║╚██╗██║██║   ██║██║╚██╗██║      ║
   ║      ╚██████╗██║  ██║██║ ╚████║╚██████╔╝██║ ╚████║      ║
   ║       ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═══╝      ║
   ║                                                          ║
   ║              E N G I N E   v{ver:<24s}         ║
   ║                                                          ║
   ╚══════════════════════════════════════════════════════════╝
""".format(ver=ENGINE_VERSION)


# ── Menu constants ───────────────────────────────────────────────────────────
_OPT_START = "start"
_OPT_SETTINGS = "settings"
_OPT_CLOSE = "close"

_MENU_OPTIONS: list[tuple[str, str, str]] = [
    ("S", _OPT_START, "Begin a new adventure or continue an existing one"),
    ("C", _OPT_SETTINGS, "Configure AI model, verbosity, and game settings"),
    ("Q", _OPT_CLOSE, "Exit Canon Engine"),
]


def _render_banner() -> None:
    """Print the title banner and version info."""
    console.print(Text(_BANNER, style=_PALETTE["title"]))
    console.print(
        Rule(title=f"[dim]{ENGINE_NAME} — AI-powered text-based RPG engine[/dim]")
    )
    console.print()


def _render_menu() -> str:
    """Display menu options and return the user's choice key (lowercase)."""
    lines: list[str] = []
    for key, _label, desc in _MENU_OPTIONS:
        lines.append(f"  [{_PALETTE['menu_key']}][{key}][/{_PALETTE['menu_key']}]  {_desc_colored(desc)}")
    console.print(Panel("\n".join(lines), title="[bold]Main Menu[/bold]", border_style="cyan"))
    choice = Prompt.ask(
        "[bold cyan]Choose[/bold cyan]",
        choices=[o[0].lower() for o in _MENU_OPTIONS],
        default="s",
    )
    return choice.lower()


def _desc_colored(desc: str) -> str:
    """Color the first word of a description as accent, rest dim."""
    parts = desc.split(" ", 1)
    if len(parts) == 2:
        return f"[{_PALETTE['accent']}]{parts[0]}[/{_PALETTE['accent']}] [{_PALETTE['dim']}]{parts[1]}[/{_PALETTE['dim']}]"
    return f"[{_PALETTE['accent']}]{desc}[/{_PALETTE['accent']}]"


# ── Settings panel ───────────────────────────────────────────────────────────

def _settings_menu(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Interactive settings editor.  Mutates and returns *settings*."""
    console.print()
    console.print(Rule(title="[bold magenta]Settings[/bold magenta]"))
    console.print()

    # AI model
    current_model = settings.get("llm_model", os.getenv("CANON_LLM_MODEL", "gpt-4o"))
    new_model = Prompt.ask(
        f"[cyan]AI Model[/cyan] (current: [yellow]{current_model}[/yellow])",
        default=current_model,
    )
    settings["llm_model"] = new_model

    # API key
    current_key = settings.get("llm_api_key", "")
    masked = ("*" * min(len(current_key), 8)) if current_key else "(not set)"
    new_key = Prompt.ask(
        f"[cyan]API Key[/cyan] (current: [dim]{masked}[/dim])",
        default="",
    )
    if new_key:
        settings["llm_api_key"] = new_key

    # Narration verbosity (0-3)
    current_verbosity = settings.get("verbosity", 2)
    new_verbosity = IntPrompt.ask(
        f"[cyan]Narration verbosity[/cyan] (0=terse, 1=brief, 2=normal, 3=verbose; current: [yellow]{current_verbosity}[/yellow])",
        default=current_verbosity,
    )
    settings["verbosity"] = max(0, min(3, new_verbosity))

    # Language style
    current_lang = settings.get("lang_style", "default")
    new_lang = Prompt.ask(
        f"[cyan]Language style[/cyan] (current: [yellow]{current_lang}[/yellow])",
        default=current_lang,
    )
    settings["lang_style"] = new_lang

    # Autosave interval (turns)
    current_autosave = settings.get("autosave_interval", 5)
    new_autosave = IntPrompt.ask(
        f"[cyan]Autosave interval (turns)[/cyan] (current: [yellow]{current_autosave}[/yellow])",
        default=current_autosave,
    )
    settings["autosave_interval"] = max(1, new_autosave)

    console.print()
    console.print("[green]✓ Settings saved.[/green]")
    console.print()
    return settings


# ── Public API ───────────────────────────────────────────────────────────────

def show_start_screen(settings: Optional[Dict[str, Any]] = None) -> str:
    """Display the start screen and return the user's top-level choice.

    Returns
    -------
    str
        One of ``"start"``, ``"settings"``, ``"close"``.
    """
    if settings is None:
        settings = {}

    _render_banner()
    choice = _render_menu()

    if choice == "s":
        return _OPT_START
    elif choice == "c":
        _settings_menu(settings)
        # Re-show after settings
        return show_start_screen(settings)
    else:
        return _OPT_CLOSE


def run_start_screen(settings: Optional[Dict[str, Any]] = None) -> str:
    """Convenience wrapper that keeps showing the menu until the user picks
    START or CLOSE (settings loops back).

    Returns
    -------
    str
        ``"start"`` or ``"close"``.
    """
    if settings is None:
        settings = {}

    while True:
        result = show_start_screen(settings)
        if result in (_OPT_START, _OPT_CLOSE):
            return result
        # settings was handled inside show_start_screen; loop back
