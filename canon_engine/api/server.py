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
        return HTMLResponse(
            html_path.read_text(encoding="utf-8"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
    return {"error": "UI not found"}


# Serve static files (JS modules, CSS, etc.)
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


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
    command_log: list = Field(default_factory=list, description="Recent command log entries.")


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
    from canon_engine.core.command_parser import parse_command
    from canon_engine.ui.game_session import _apply_parsed, step_session_turn, build_layout_payload
    import random as _random_mod

    state = _get_or_load_state(req.slot)

    # Use step_session_turn as the primary orchestrator
    rng = _random_mod.Random()
    turn_result = step_session_turn(state, req.command, rng)

    narration = turn_result.get("narration", "")
    layout_data = turn_result.get("layout", {})
    command_log = turn_result.get("command_log", [])

    # Auto-save after each action
    _save_session(req.slot)

    return ActionResponse(
        narration=narration,
        layout=layout_data,
        state=state,
        command_log=command_log,
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
    race: Optional[str] = Field(default=None, description="Character race (e.g. 'Human', 'Robot-Android', 'Cat-Humanoid').")
    archetype: Optional[str] = Field(default=None, description="Character archetype/class (e.g. 'knight', 'mage', 'warlock cat humanoid').")
    traits: Optional[str] = Field(default=None, description="Extra character traits/descriptors (free text).")
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
    race = req.race or preset_data.get("race", "Human")
    archetype = req.archetype or preset_data.get("archetype", "Adventurer")
    traits = req.traits or ""
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
        "race": race,
        "archetype": archetype,
        "traits": traits,
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
    state["combat"] = {"active": False, "enemies": [], "active_enemy_index": 0, "round": 0, "turn": "player", "initiative_order": [], "current_turn_index": 0, "player_dodging": False, "defeated_enemies": []}
    state["companions"] = []
    state["quests"] = {"active": {}, "completed": {}, "failed": {}}
    state["world_log"] = [f"{char_name} awakens at {location}."]

    # Generate narration
    race_str = f" {race}" if race and race.lower() != "human" else ""
    traits_str = f" [{traits}]" if traits else ""
    narration = (
        f"**{char_name}** the{race_str} {archetype}{traits_str} has entered the world.\n\n"
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

def _save_metadata(f: Path) -> Dict[str, Any]:
    """Extract metadata from a save file."""
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        # Try 'player' first (current format), then 'hero' (legacy)
        player = data.get("player") or data.get("hero") or {}
        world = data.get("world", {})
        return {
            "slot": f.stem,
            "size_bytes": f.stat().st_size,
            "modified": f.stat().st_mtime,
            "character_name": player.get("name", "Unknown"),
            "race": player.get("race", ""),
            "class_name": player.get("archetype") or player.get("class_name", ""),
            "level": player.get("level", 1),
            "genre": world.get("setting_primary") or world.get("genre") or data.get("genre", ""),
            "location": world.get("location_name") or world.get("location") or data.get("location", ""),
            "hp": player.get("hp", 0) or data.get("hp", 0),
            "max_hp": player.get("max_hp", 0) or data.get("max_hp", 0),
        }
    except Exception:
        return {
            "slot": f.stem,
            "size_bytes": f.stat().st_size,
            "modified": f.stat().st_mtime,
            "character_name": "Corrupted",
            "race": "",
            "class_name": "",
            "level": 0,
            "genre": "",
            "location": "",
            "hp": 0,
            "max_hp": 0,
        }


@app.get("/saves")
async def list_saves(
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """List all save files with metadata."""
    from canon_engine.state_manager import _saves_dir
    saves_dir = _saves_dir()
    saves = []
    if saves_dir.exists():
        for f in sorted(saves_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            saves.append(_save_metadata(f))
    return {"saves": saves}


class SaveActionRequest(BaseModel):
    """Body for save management actions."""
    slot: str = Field(..., description="Source save slot name.")
    target: str = Field(default="", description="Target slot name (for duplicate/rename).")


@app.post("/saves/delete")
async def delete_save(
    req: SaveActionRequest,
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """Delete a save file."""
    from canon_engine.state_manager import _saves_dir
    saves_dir = _saves_dir()
    save_path = saves_dir / f"{req.slot}.json"
    if not save_path.exists():
        raise HTTPException(status_code=404, detail=f"Save '{req.slot}' not found.")
    save_path.unlink()
    # Remove from cache if loaded
    _sessions.pop(req.slot, None)
    return {"status": "deleted", "slot": req.slot}


@app.post("/saves/duplicate")
async def duplicate_save(
    req: SaveActionRequest,
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """Duplicate a save file to a new slot."""
    from canon_engine.state_manager import _saves_dir
    saves_dir = _saves_dir()
    src_path = saves_dir / f"{req.slot}.json"
    if not src_path.exists():
        raise HTTPException(status_code=404, detail=f"Save '{req.slot}' not found.")
    target_name = req.target or f"{req.slot} (copy)"
    dst_path = saves_dir / f"{target_name}.json"
    import shutil
    shutil.copy2(src_path, dst_path)
    return {"status": "duplicated", "slot": req.slot, "target": target_name}


@app.post("/saves/rename")
async def rename_save(
    req: SaveActionRequest,
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """Rename a save file."""
    from canon_engine.state_manager import _saves_dir
    saves_dir = _saves_dir()
    src_path = saves_dir / f"{req.slot}.json"
    if not src_path.exists():
        raise HTTPException(status_code=404, detail=f"Save '{req.slot}' not found.")
    if not req.target:
        raise HTTPException(status_code=400, detail="Target name required for rename.")
    dst_path = saves_dir / f"{req.target}.json"
    if dst_path.exists():
        raise HTTPException(status_code=409, detail=f"Save '{req.target}' already exists.")
    src_path.rename(dst_path)
    # Update cache key if loaded
    if req.slot in _sessions:
        _sessions[req.target] = _sessions.pop(req.slot)
    return {"status": "renamed", "slot": req.slot, "target": req.target}


# ── Codex ───────────────────────────────────────────────────────────────────

@app.get("/codex")
async def get_codex(
    slot: str = "default",
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """Return the codex (lore entries) for a save slot."""
    state = _get_or_load_state(slot)
    return {"codex": state.get("lore_entries", [])}


# ── Quests (structured) ────────────────────────────────────────────────────

@app.get("/quests")
async def get_quests(
    slot: str = "default",
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """Return the quest log for a save slot."""
    state = _get_or_load_state(slot)
    quests = state.get("quests", {})
    if isinstance(quests, dict):
        return {
            "active": quests.get("active", []),
            "completed": quests.get("completed", []),
        }
    return {"active": quests if isinstance(quests, list) else [], "completed": []}


# ── Manual (alias for handbook) ────────────────────────────────────────────

@app.get("/manual")
async def get_manual(
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """Return handbook topics (alias for /handbook)."""
    topics = _load_handbook()
    if isinstance(topics, dict):
        return {
            "topics": [
                {"id": k, "title": v.get("title", k) if isinstance(v, dict) else k}
                for k, v in topics.items()
            ]
        }
    return {"topics": []}


# ── Equipment Slots ────────────────────────────────────────────────────────

@app.get("/equipment/slots")
async def get_equipment_slots(
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """Return the 17 equipment slot definitions."""
    from canon_engine.core.inventory import EQUIP_SLOTS
    return {"slots": [{"key": k, "label": v} for k, v in EQUIP_SLOTS.items()]}


# ── Me (current user info) ────────────────────────────────────────────────

@app.get("/me")
async def get_me(
    slot: str = "default",
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """Return current user/player info."""
    state = _get_or_load_state(slot)
    player = state.get("player", {})
    return {
        "username": player.get("name", "Adventurer"),
        "level": player.get("level", 1),
        "archetype": player.get("archetype", ""),
        "genre": state.get("genre", state.get("world", {}).get("setting_primary", "")),
    }


# ── API Key Settings ──────────────────────────────────────────────────────

class APIKeyRequest(BaseModel):
    """Body for POST /settings/keys."""
    provider: str = Field(..., description="Key provider (e.g. 'openrouter', 'openai').")
    api_key: str = Field(..., description="The API key value.")


@app.get("/settings/keys")
async def get_api_keys(
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """Return which API key providers are configured (values are masked)."""
    providers = {}
    for key_name in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "CANON_LLM_API_KEY"):
        val = os.getenv(key_name, "")
        provider = key_name.replace("_API_KEY", "").replace("CANON_LLM", "CANON").lower()
        providers[provider] = {"configured": bool(val), "masked": f"***{val[-4:]}" if len(val) > 4 else ""}
    return {"providers": providers}


@app.post("/settings/keys")
async def set_api_key(
    req: APIKeyRequest,
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """Set an API key at runtime (in-memory only, not persisted to .env)."""
    env_map = {
        "openrouter": "OPENROUTER_API_KEY",
        "openai": "OPENAI_API_KEY",
        "canon": "CANON_LLM_API_KEY",
    }
    env_name = env_map.get(req.provider.lower())
    if not env_name:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{req.provider}'. Use: {list(env_map.keys())}")
    os.environ[env_name] = req.api_key
    return {"status": "set", "provider": req.provider, "env_var": env_name}


# ── Backstory Generation ──────────────────────────────────────────────────

class BackstoryRequest(BaseModel):
    """Body for POST /backstory."""
    name: str = Field(default="Adventurer", description="Character name.")
    archetype: str = Field(default="adventurer", description="Character archetype.")
    race: str = Field(default="human", description="Character race.")
    gender: str = Field(default="", description="Character gender.")
    genre: str = Field(default="medieval_fantasy", description="World genre.")


@app.post("/backstory")
async def generate_backstory_endpoint(
    req: BackstoryRequest,
    _auth: None = Depends(_verify_auth),
) -> Dict[str, Any]:
    """Generate a backstory for a character."""
    from canon_engine.core.backstory import generate_backstory
    character = {
        "name": req.name,
        "archetype": req.archetype,
        "race": req.race,
        "gender": req.gender,
        "genre": req.genre,
    }
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    backstory = generate_backstory(character, api_key=api_key)
    return {"backstory": backstory, "character": character}


# ── Run helper ───────────────────────────────────────────────────────────────

def run_server(host: str = "127.0.0.1", port: int = 8787) -> None:
    """Start the Uvicorn server."""
    import uvicorn
    logger.info("Starting Canon Engine API on %s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
