"""
Canon Engine — Backstory Generator

Generates character backstories via LLM or template fallback.

Public API:
    generate_backstory(character: dict, api_key: str = None) -> str
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Template backstories by archetype
# ---------------------------------------------------------------------------

_BACKSTORY_TEMPLATES = {
    "knight": (
        "{name} was once a sworn blade of the {realm}, until the order fell to betrayal. "
        "Now a wandering knight without a banner, {name} seeks to restore honor — not to a kingdom, "
        "but to a promise made to someone who trusted {pronoun_obj} with their life. "
        "The weight of a broken oath is heavier than any armor."
    ),
    "rogue": (
        "{name} grew up in the underbelly of {city}, stealing to survive and charming to thrive. "
        "A deal gone wrong left {pronoun_obj} indebted to a shadowy syndicate, and now every alley "
        "could hide an assassin — or an opportunity. Trust is a currency {name} can rarely afford."
    ),
    "mage": (
        "{name}'s gift for the arcane manifested early, scorching a library shelf at age seven. "
        "Taken in by the {academy}, {pronoun_sub} proved brilliant but restless — always reaching "
        "for spells deemed too dangerous. When a forbidden text vanished from the archives, "
        "{name} left to find it before someone else did."
    ),
    "ranger": (
        "The wilds raised {name} more than any village. An orphan found by a trapper, "
        "{pronoun_sub} learned to read tracks before letters and to trust animals before people. "
        "Now the forest speaks to {pronoun_obj} in warnings — something dark is moving through "
        "the trees, and {name} may be the only one who can read its trail."
    ),
    "cleric": (
        "{name} answered a divine calling at the temple of {deity}, drawn by visions of a "
        "light that pushed back the dark. But faith is tested in the field, not the pew — "
        "and the miracles {pronoun_sub} performs draw attention from those who would "
        "weaponize the divine. {name} walks a line between healer and warrior."
    ),
    "bard": (
        "{name} left home with a lute and a lie — that {pronoun_sub} knew a song that could "
        "change the world. Somewhere between the taverns and the wars, the lie became true. "
        "Now {name} travels gathering stories, convinced that the right tale told at the right "
        "moment can save more lives than any sword."
    ),
    "adventurer": (
        "{name} has always been drawn to the edges of the map, where the ink fades and "
        "the known world gives way to rumor. A jack-of-all-trades and master of none, "
        "{pronoun_sub} has survived by wits, luck, and the stubborn refusal to stay down. "
        "The next horizon always calls."
    ),
}

# Fallback for unknown archetypes
_DEFAULT_BACKSTORY = (
    "{name}'s past is a patchwork of roads traveled and debts unpaid. "
    "A {archetype} of modest skill and immodest ambition, {pronoun_sub} set out into the world "
    "seeking something {pronoun_sub} couldn't name — only that it waited beyond the next hill."
)


# ---------------------------------------------------------------------------
# Pronoun helpers
# ---------------------------------------------------------------------------

def _get_pronouns(gender: str) -> dict:
    """Return pronoun dict based on gender string."""
    gender = gender.lower().strip()
    if gender in ("female", "f", "woman", "she"):
        return {"sub": "she", "obj": "her", "pos": "her", "ref": "herself"}
    if gender in ("they", "nonbinary", "nb", "neutral"):
        return {"sub": "they", "obj": "them", "pos": "their", "ref": "themselves"}
    # Default masculine
    return {"sub": "he", "obj": "him", "pos": "his", "ref": "himself"}


# ---------------------------------------------------------------------------
# Template fallback
# ---------------------------------------------------------------------------

def _template_backstory(character: dict) -> str:
    """Generate a backstory from templates."""
    name = character.get("name", "The adventurer")
    archetype = character.get("archetype", "adventurer").lower()
    gender = character.get("gender", "")
    pronouns = _get_pronouns(gender)

    template = _BACKSTORY_TEMPLATES.get(archetype, _DEFAULT_BACKSTORY)

    # Fill in placeholders with reasonable defaults
    fill = {
        "name": name,
        "archetype": archetype,
        "pronoun_sub": pronouns["sub"],
        "pronoun_obj": pronouns["obj"],
        "pronoun_pos": pronouns["pos"],
        "pronoun_ref": pronouns["ref"],
        "realm": "the Silver Crown",
        "city": "the port of Greyhaven",
        "academy": "the Arcanum",
        "deity": "the Lightbringer",
    }

    try:
        return template.format(**fill)
    except KeyError:
        # If a placeholder is missing, do a simple replacement
        text = template
        for key, val in fill.items():
            text = text.replace(f"{{{key}}}", val)
        return text


# ---------------------------------------------------------------------------
# LLM-based generation
# ---------------------------------------------------------------------------

def _llm_backstory(character: dict, api_key: str, base_url: str) -> Optional[str]:
    """Generate backstory via LLM. Returns None on failure."""
    try:
        from openai import OpenAI
    except ImportError:
        return None

    name = character.get("name", "Adventurer")
    archetype = character.get("archetype", "adventurer")
    race = character.get("race", "human")
    genre = character.get("genre", character.get("setting", "medieval_fantasy"))
    gender = character.get("gender", "")
    stats = character.get("stats", {})

    stats_str = ", ".join(f"{k}:{v}" for k, v in stats.items()) if stats else "balanced"

    prompt = (
        f"Generate a 3-6 sentence backstory for a tabletop RPG character.\n\n"
        f"Name: {name}\n"
        f"Archetype: {archetype}\n"
        f"Race: {race}\n"
        f"Gender: {gender or 'unspecified'}\n"
        f"Genre/Setting: {genre}\n"
        f"Stats: {stats_str}\n\n"
        f"Write in third person. Make it vivid and specific — include a hook, a motivation, "
        f"and a hint of mystery. Do NOT use generic phrases like 'destiny awaits'. "
        f"Return ONLY the backstory text, no title or preamble."
    )

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=os.getenv("NARRATOR_MODEL", "google/gemini-2.0-flash-001"),
            messages=[
                {"role": "system", "content": "You are a creative writer specializing in tabletop RPG character backstories."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.9,
            max_tokens=300,
        )
        text = response.choices[0].message.content or ""
        return text.strip() if text.strip() else None
    except Exception as exc:
        logger.error("LLM backstory generation failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_backstory(character: dict, api_key: Optional[str] = None) -> str:
    """
    Generate a character backstory.

    Parameters
    ----------
    character : dict
        Character data with at least 'name' and 'archetype'.
    api_key : str, optional
        OpenAI-compatible API key. Falls back to env vars, then template.

    Returns
    -------
    str
        3-6 sentence backstory text.
    """
    # Resolve API key
    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")

    if api_key:
        base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        result = _llm_backstory(character, api_key, base_url)
        if result:
            return result

    # Fallback to template
    return _template_backstory(character)
