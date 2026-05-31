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

# CORS for localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# ── Run helper ───────────────────────────────────────────────────────────────

def run_server(host: str = "127.0.0.1", port: int = 8787) -> None:
    """Start the Uvicorn server."""
    import uvicorn
    logger.info("Starting Canon Engine API on %s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
