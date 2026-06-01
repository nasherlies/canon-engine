"""FastAPI HTTP bridge for Canon Engine.

Provides a REST API so web front-ends and bots can drive the engine without
the Rich terminal UI.

Endpoints
---------
POST /action         — Main game action (command + slot)
GET  /health         — Health check with dev_mode flag
GET  /handbook       — Handbook topics list
GET  /handbook/{id}  — Single handbook topic
GET  /journal        — World log

Auth: ``Authorization: Bearer <ADMIN_PASSWORD>`` (from env ``ADMIN_PASSWORD``).
Runs on 127.0.0.1:8787.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from canon_engine import state_manager
from canon_engine.config import Config

logger = logging.getLogger(__name__)

# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Canon Engine API",
    version="0.1.0",
    description="AI-powered text-based infinite RPG engine — HTTP bridge",
)

# CORS for localhost + tunnel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the web UI at /
_STATIC_DIR = Path(__file__).parent / "static"

@app.get("/", include_in_schema=False)
async def serve_ui():
    """Serve the main web UI."""
    html_path = _STATIC_DIR / "index.html"
    if html_path.exists():
        from fastapi.responses import HTMLResponse
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return {"error": "UI not found"}


# ── Auth ─────────────────────────────────────────────────────────────────────

def _get_admin_password() -> str:
    """Read the admin password from env."""
    return os.getenv("ADMIN_PASSWORD", "")


async def _verify_auth(authorization: Optional[str] = Header(None)) -> None:
    """Verify the Authorization header if ADMIN_PASSWORD is set.

    If no ADMIN_PASSWORD is configured, auth is skipped (dev mode).
    """
    admin_pw = _get_admin_password()
    if not admin_pw:
        return  # No password set → open access (dev mode)

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")

    # Accept "Bearer <password>" or raw password
    token = authorization
    if token.startswith("Bearer "):
        token = token[7:]

    if token != admin_pw:
        raise HTTPException(status_code=403, detail="Invalid credentials.")


# ── Session management ───────────────────────────────────────────────────────

# In-memory session cache (slot → state dict).  In production, use Redis or similar.
_sessions: Dict[str, Dict[str, Any]] = {}


def _get_or_load_state(slot: str) -> Dict[str, Any]:
    """Load state for *slot* from cache or disk."""
    if slot in _sessions:
        return _sessions[slot]

    try:
        state = state_manager.load_state(slot)
    except FileNotFoundError:
        state = state_manager.new_state()
    except Exception as exc:
        logger.warning("Failed to load slot %r: %s — creating new.", slot, exc)
        state = state_manager.new_state()

    _sessions[slot] = state
    return state


def _save_session(slot: str) -> None:
    """Persist a session to disk."""
    state = _sessions.get(slot)
    if state is not None:
        try:
            state_manager.save_state(state, slot)
        except Exception as exc:
            logger.error("Failed to save slot %r: %s", slot, exc)


# ── Request / response models ────────────────────────────────────────────────

class ActionRequest(BaseModel):
    """Body for POST /action."""
    command: str = Field(..., description="The player's command text (e.g. '/look sword').")
    slot: str = Field(default="default", description="Save slot name.")


class ActionResponse(BaseModel):
    """Response from POST /action."""
    narration: str = Field(default="", description="AI narration output.")
    layout: Dict[str, Any] = Field(default_factory=dict, description="Layout data for UI rendering.")
    state: Dict[str, Any] = Field(default_factory=dict, description="Updated game state snapshot.")


class HealthResponse(BaseModel):
    """Response from GET /health."""
    status: str = "ok"
    version: str = "0.1.0"
    dev_mode: bool = False


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check with dev_mode flag."""
    dev_mode = not bool(_get_admin_password())
    return HealthResponse(status="ok", version="0.1.0", dev_mode=dev_mode)


@app.post("/action", response_model=ActionResponse)
async def handle_action(
    req: ActionRequest,
    _auth: None = Depends(_verify_auth),
) -> ActionResponse:
    """Process a player command and return narration + layout + state.

    This is the main game loop entry point for API clients.
    """
    from core.command_parser import parse_command
    from canon_engine.ui.game_session import _apply_parsed

    state = _get_or_load_state(req.slot)
    parsed = parse_command(req.command)

    # Apply the command
    result = _apply_parsed(state, parsed, config=Config())

    narration = result.get("narration", "")
    layout_data = result.get("layout")
    if layout_data is None:
        from canon_engine.ui.game_layout import render_layout_dict
        layout_data = render_layout_dict(state, narration)

    # Auto-save after each action
    _save_session(req.slot)

    return ActionResponse(
        narration=narration,
        layout=layout_data,
        state=state,
    )


# ── Handbook ─────────────────────────────────────────────────────────────────

_HANDBOOK_PATH = Path(__file__).resolve().parent.parent.parent / "content" / "handbook" / "topics.json"


def _load_handbook() -> Dict[str, Any]:
    """Load the handbook topics from disk."""
    if not _HANDBOOK_PATH.exists():
        return {}
    try:
        return json.loads(_HANDBOOK_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


@app.get("/handbook")
async def get_handbook(
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """Return the list of handbook topic IDs and titles."""
    topics = _load_handbook()
    if isinstance(topics, dict):
        return {
            "topics": [
                {"id": k, "title": v.get("title", k) if isinstance(v, dict) else k}
                for k, v in topics.items()
            ]
        }
    return {"topics": []}


@app.get("/handbook/{topic_id}")
async def get_handbook_topic(
    topic_id: str,
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """Return a single handbook topic."""
    topics = _load_handbook()
    if isinstance(topics, dict) and topic_id in topics:
        return {"id": topic_id, **topics[topic_id]}
    raise HTTPException(status_code=404, detail=f"Handbook topic '{topic_id}' not found.")


# ── Journal ──────────────────────────────────────────────────────────────────

@app.get("/journal")
async def get_journal(
    slot: str = "default",
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """Return the world log (journal) for a save slot."""
    state = _get_or_load_state(slot)
    world_log = state.get("world_log", [])
    return {"journal": world_log[-100:]}  # Last 100 entries


# ── Presets ───────────────────────────────────────────────────────────────────

@app.get("/presets")
async def get_presets(
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """Return character presets from content/presets/characters.json."""
    presets_path = Path(__file__).resolve().parent.parent.parent / "content" / "presets" / "characters.json"
    if not presets_path.exists():
        return {"presets": {}}
    try:
        return {"presets": json.loads(presets_path.read_text(encoding="utf-8"))}
    except Exception as exc:
        logger.error("Failed to load presets: %s", exc)
        return {"presets": {}}


# ── World Settings ───────────────────────────────────────────────────────────

@app.get("/world_settings")
async def get_world_settings(
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """Return world setting options: genres, locations, speech styles."""
    return {
        "genres": {
            "medieval_fantasy": {
                "name": "Medieval Fantasy",
                "description": "Swords, sorcery, and ancient kingdoms.",
                "starting_locations": [
                    "The Crossroads Inn",
                    "Ashenvale Village",
                    "The King's Gate",
                    "Dungeon Entrance",
                    "Forest Clearing",
                ],
            },
            "space_opera": {
                "name": "Space Opera",
                "description": "Galactic empires, starships, and alien diplomacy.",
                "starting_locations": [
                    "Starport Delta",
                    "The Bridge of the Horizon",
                    "Alien Market on Zyphis",
                    "Cryo-Bay Awakening",
                    "Rebel Outpost",
                ],
            },
            "gothic_horror": {
                "name": "Gothic Horror",
                "description": "Crumbling manors, dark secrets, and things that lurk.",
                "starting_locations": [
                    "Ravenmoor Manor Gate",
                    "The Foggy Graveyard",
                    "Abandoned Asylum",
                    "Cathedral Ruins",
                    "Village Square at Dusk",
                ],
            },
            "western": {
                "name": "Western",
                "description": "Dusty trails, six-shooters, and frontier justice.",
                "starting_locations": [
                    "Dusty Gulch Train Station",
                    "The Saloon",
                    "Ridge Overlook",
                    "Canyon Mouth",
                    "Sheriff's Office",
                ],
            },
            "anime_dramatic": {
                "name": "Anime Dramatic",
                "description": "High-stakes emotion, legendary power, and dramatic flair.",
                "starting_locations": [
                    "Academy Courtyard",
                    "Shrine on the Mountain",
                    "Neon City Rooftop",
                    "The Forbidden Forest",
                    "Colosseum Entrance",
                ],
            },
        },
        "speech_styles": [
            "western_drawl",
            "sly_whisper",
            "scholarly",
            "gruff",
            "gentle",
            "terse",
            "theatrical",
            "formal",
            "street_slang",
            "poetic",
            "stoic",
            "cheerful",
        ],
    }


# ── Start Character ──────────────────────────────────────────────────────────

class StartCharacterRequest(BaseModel):
    """Body for POST /start_character."""
    preset_id: Optional[str] = Field(default=None, description="Character preset ID (e.g. 'garros').")
    name: Optional[str] = Field(default=None, description="Character name (overrides preset).")
    archetype: Optional[str] = Field(default=None, description="Character archetype (e.g. 'knight', 'mage').")
    stats: Optional[Dict[str, int]] = Field(default=None, description="Stats dict: STR, DEX, INT, CHA, CON, LCK.")
    speech_style: Optional[str] = Field(default=None, description="NPC narrator speech style.")
    setting_primary: Optional[str] = Field(default="medieval_fantasy", description="Primary genre.")
    setting_secondary: Optional[str] = Field(default=None, description="Secondary genre.")
    starting_location: Optional[str] = Field(default=None, description="Starting location name.")
    slot: str = Field(default="default", description="Save slot name.")


@app.post("/start_character", response_model=ActionResponse)
async def start_character(
    req: StartCharacterRequest,
    _auth: None = Depends(_verify_auth),
) -> ActionResponse:
    """Create a new character and initialise a fresh game state.

    Either supply ``preset_id`` to load from presets, or supply ``name``,
    ``archetype``, ``stats``, etc. for a custom character.
    """
    from canon_engine.systems.character import create_character as _create_char, max_hp as _max_hp, score_to_modifier

    # --- Load preset data if requested ---
    preset_data: Dict[str, Any] = {}
    if req.preset_id:
        presets_path = Path(__file__).resolve().parent.parent.parent / "content" / "presets" / "characters.json"
        if presets_path.exists():
            try:
                all_presets = json.loads(presets_path.read_text(encoding="utf-8"))
                preset_data = all_presets.get(req.preset_id, {})
            except Exception:
                pass
        if not preset_data:
            raise HTTPException(status_code=404, detail=f"Preset '{req.preset_id}' not found.")

    # --- Build character ---
    char_name = req.name or preset_data.get("name", "Adventurer")
    archetype = req.archetype or preset_data.get("archetype", "Adventurer")
    stats = req.stats or preset_data.get("stats", {})
    speech_style = req.speech_style or preset_data.get("speech_style", "default")
    starting_gear = preset_data.get("starting_gear", [])

    # If still no stats, generate random ones via create_character
    if not stats:
        fresh = _create_char(char_name, klass=archetype)
        stats = fresh["stats"]

    # Ensure all 6 stats present
    for s in ("STR", "DEX", "INT", "CHA", "CON", "LCK"):
        stats.setdefault(s, 10)

    con = stats.get("CON", 10)
    hp = _max_hp(con)
    dex = stats.get("DEX", 10)

    # Build inventory from starting gear
    inventory = [{"name": g, "rarity": "common", "qty": 1} for g in starting_gear]
    if not inventory:
        inventory = [{"name": "health_potion", "rarity": "common", "qty": 2}]

    # --- Build world ---
    setting_primary = req.setting_primary or "medieval_fantasy"
    setting_secondary = req.setting_secondary

    # Resolve starting location
    location = req.starting_location
    if not location:
        _genres = {
            "medieval_fantasy": "The Crossroads Inn",
            "space_opera": "Starport Delta",
            "gothic_horror": "Ravenmoor Manor Gate",
            "western": "Dusty Gulch Train Station",
            "anime_dramatic": "Academy Courtyard",
        }
        location = _genres.get(setting_primary, "The Crossroads Inn")

    # --- Assemble state ---
    state = state_manager.new_state()
    state["player"] = {
        "name": char_name,
        "archetype": archetype,
        "level": 1,
        "xp": 0,
        "xp_next": 100,
        "stats": stats,
        "hp": hp,
        "max_hp": hp,
        "mp": stats.get("INT", 10) * 3,
        "max_mp": stats.get("INT", 10) * 3,
        "stamina": 80,
        "max_stamina": 80,
        "ac": 10 + score_to_modifier(dex),
        "proficiency_bonus": 2,
        "skill_points": 0,
        "skills": [],
        "conditions": [],
        "gold": 50,
        "inventory": inventory,
        "speech_style": speech_style,
    }
    state["world"] = {
        "setting_primary": setting_primary,
        "setting_secondary": setting_secondary,
        "location_id": location.lower().replace(" ", "_"),
        "location_name": location,
        "weather": "clear",
        "minutes_total": 480,  # 8:00 AM
        "locations": {
            location.lower().replace(" ", "_"): {"name": location, "discovered": True}
        },
    }
    state["combat"] = {"active": False, "enemies": [], "active_enemy_index": 0, "round": 0, "turn": "player"}
    state["companions"] = []
    state["quests"] = []
    state["world_log"] = [f"{char_name} awakens at {location}."]

    # Generate narration
    narration = (
        f"**{char_name}** the {archetype} has entered the world.\n\n"
        f"Location: {location}\n"
        f"HP: {hp}/{hp}  |  AC: {state['player']['ac']}\n"
        f"Speech Style: {speech_style}\n\n"
    )
    if inventory:
        item_names = ", ".join(i["name"] for i in inventory)
        narration += f"Starting gear: {item_names}\n\n"
    narration += "Your adventure begins. Type `/help` for commands."

    # Layout + save
    from canon_engine.ui.game_layout import render_layout_dict
    layout_data = render_layout_dict(state, narration)
    _sessions[req.slot] = state
    _save_session(req.slot)

    return ActionResponse(narration=narration, layout=layout_data, state=state)


# ── Encounter ────────────────────────────────────────────────────────────────

class EncounterRequest(BaseModel):
    """Body for POST /encounter."""
    slot: str = Field(default="default", description="Save slot name.")
    enemy_count: Optional[int] = Field(default=None, description="Number of enemies (1-3). Random if omitted.")


@app.post("/encounter", response_model=ActionResponse)
async def trigger_encounter(
    req: EncounterRequest,
    _auth: None = Depends(_verify_auth),
) -> ActionResponse:
    """Generate a random encounter from enemies.json and start combat."""
    import random as _random
    from canon_engine.systems.combat import start_combat as _start_combat

    state = _get_or_load_state(req.slot)

    # Load enemies.json
    enemies_path = Path(__file__).resolve().parent.parent.parent / "content" / "enemies.json"
    if not enemies_path.exists():
        raise HTTPException(status_code=500, detail="enemies.json not found.")
    try:
        enemies_data = json.loads(enemies_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load enemies: {exc}")

    enemy_pool = enemies_data.get("enemies", [])
    if not enemy_pool:
        raise HTTPException(status_code=404, detail="No enemies defined.")

    # Filter out tutorial dummy and zero-weight enemies
    eligible = [e for e in enemy_pool if e.get("encounter_weight", 0) > 0]
    if not eligible:
        eligible = enemy_pool

    weights = [e.get("encounter_weight", 1) for e in eligible]

    # Pick 1-3 enemies
    count = req.enemy_count if req.enemy_count else _random.randint(1, 3)
    count = max(1, min(count, 3))

    chosen = []
    for _ in range(count):
        pick = _random.choices(eligible, weights=weights, k=1)[0]
        enemy_copy = {
            "name": pick["name"],
            "hp": pick["hp"],
            "max_hp": pick["max_hp"],
            "ac": pick["ac"],
            "attack_bonus": pick.get("str", 10) // 2 + 2,
            "damage_dice": "1d6",
            "xp_value": pick.get("xp_value", 10),
            "description": pick.get("description", ""),
        }
        chosen.append(enemy_copy)

    _start_combat(state, chosen)

    enemy_names = ", ".join(e["name"] for e in chosen)
    narration = (
        f"⚔ **Encounter!**\n\n"
        f"You are ambushed by: {enemy_names}!\n\n"
    )
    for e in chosen:
        narration += f"• **{e['name']}** — HP: {e['hp']}/{e['max_hp']}, AC: {e['ac']}\n"
    narration += "\nUse `/attack` to strike, `/block` to defend, or `/flee` to run!"

    from canon_engine.ui.game_layout import render_layout_dict
    layout_data = render_layout_dict(state, narration)
    _save_session(req.slot)

    return ActionResponse(narration=narration, layout=layout_data, state=state)


# ── Saves ────────────────────────────────────────────────────────────────────

@app.get("/saves")
async def list_saves(
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """List all save files in the saves/ directory."""
    from canon_engine.state_manager import _saves_dir
    saves_dir = _saves_dir()
    saves = []
    if saves_dir.exists():
        for f in sorted(saves_dir.glob("*.json")):
            saves.append({
                "slot": f.stem,
                "size_bytes": f.stat().st_size,
                "modified": f.stat().st_mtime,
            })
    return {"saves": saves}


# ── Run helper ───────────────────────────────────────────────────────────────

def run_server(host: str = "127.0.0.1", port: int = 8787) -> None:
    """Start the Uvicorn server."""
    import uvicorn
    logger.info("Starting Canon Engine API on %s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
