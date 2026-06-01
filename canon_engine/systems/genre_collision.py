"""
Genre Collision System for Canon Engine.

Blends two genres together into coherent, creative mashup settings.
Each collision produces a unique template with locations, enemies,
narrative style, and ready-made opening narration.
"""

import json
import os
from typing import Optional


_COLLISIONS: list[dict] = []
_BY_PAIR: dict[tuple[str, str], dict] = {}
_BY_ID: dict[str, dict] = {}
_LOADED = False


def _data_path() -> str:
    """Locate genre_collisions.json relative to the project root."""
    # Try several candidate paths
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "content", "genre_collisions.json"),
        os.path.join(os.getcwd(), "content", "genre_collisions.json"),
        os.path.expanduser("~/canon-engine/content/genre_collisions.json"),
    ]
    for p in candidates:
        resolved = os.path.abspath(p)
        if os.path.isfile(resolved):
            return resolved
    raise FileNotFoundError(
        "genre_collisions.json not found. Searched:\n"
        + "\n".join(f"  - {os.path.abspath(c)}" for c in candidates)
    )


def _load() -> None:
    """Load collision templates from disk (idempotent)."""
    global _COLLISIONS, _BY_PAIR, _BY_ID, _LOADED
    if _LOADED:
        return
    path = _data_path()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _COLLISIONS = data.get("collisions", [])
    _BY_PAIR.clear()
    _BY_ID.clear()
    for coll in _COLLISIONS:
        cid = coll.get("id", "")
        genres = coll.get("genres", [])
        _BY_ID[cid] = coll
        if len(genres) == 2:
            _BY_PAIR[(genres[0], genres[1])] = coll
            _BY_PAIR[(genres[1], genres[0])] = coll  # reverse lookup
    _LOADED = True


def get_collision(genre_a: str, genre_b: str) -> Optional[dict]:
    """
    Return the collision template for a genre pair, or None.

    Args:
        genre_a: First genre identifier (e.g. "medieval_fantasy")
        genre_b: Second genre identifier (e.g. "space_opera")

    Returns:
        Collision template dict, or None if no match.
    """
    _load()
    key = (genre_a.strip().lower(), genre_b.strip().lower())
    return _BY_PAIR.get(key)


def list_collisions() -> list[dict]:
    """
    Return all available collision templates.

    Returns:
        List of collision template dicts.
    """
    _load()
    return list(_COLLISIONS)


def get_collision_by_id(collision_id: str) -> Optional[dict]:
    """
    Look up a collision template by its unique id.

    Args:
        collision_id: The collision's id string.

    Returns:
        Collision template dict, or None.
    """
    _load()
    return _BY_ID.get(collision_id)


def apply_collision(state: dict, collision_id: str) -> dict:
    """
    Apply a collision template to an active game state.

    Merges the collision's setting overrides, narrative style, and
    enemy types into the game state so the narrator uses them.

    Args:
        state: The current game state dict (will be mutated and returned).
        collision_id: The collision id to apply.

    Returns:
        The mutated state dict with collision data merged in.

    Raises:
        ValueError: If collision_id is not found.
    """
    _load()
    coll = _BY_ID.get(collision_id)
    if coll is None:
        raise ValueError(f"Unknown collision id: {collision_id!r}")

    # Store the active collision reference
    state["active_collision"] = {
        "id": coll["id"],
        "name": coll["name"],
        "genres": list(coll["genres"]),
    }

    # Merge setting overrides
    overrides = coll.get("setting_overrides", {})
    state.setdefault("setting_overrides", {})
    for key, val in overrides.items():
        state["setting_overrides"][key] = val

    # Merge narrative style
    style = coll.get("narrative_style", {})
    state["narrative_style"] = {
        "tone": style.get("tone", ""),
        "vocabulary": list(style.get("vocabulary", [])),
        "themes": list(style.get("themes", [])),
    }

    # Merge enemy types
    state["enemy_types"] = list(coll.get("enemy_types", []))

    # Store opening narration for use at adventure start
    state["opening_narration"] = coll.get("opening_narration", "")

    # Update genre field
    state["genre"] = coll["id"]
    state["genre_name"] = coll["name"]

    return state


def describe_collision(genre_a: str, genre_b: str) -> Optional[str]:
    """
    Return a human-readable description of the collision, or None.

    Args:
        genre_a: First genre identifier.
        genre_b: Second genre identifier.

    Returns:
        Formatted description string, or None if no collision exists.
    """
    coll = get_collision(genre_a, genre_b)
    if coll is None:
        return None
    lines = [
        f"⚡ {coll['name']}",
        f"  Genres: {coll['genres'][0]} × {coll['genres'][1]}",
        f"  {coll['description']}",
        "",
        f"  Tone: {coll.get('narrative_style', {}).get('tone', 'N/A')}",
        f"  Locations: {', '.join(coll.get('setting_overrides', {}).get('location_names', [])[:4])}...",
    ]
    return "\n".join(lines)
