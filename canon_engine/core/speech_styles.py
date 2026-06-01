"""
Canon Engine — Speech Styles

Provides speech-style prompt modifiers loaded from content/languages/*.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CONTENT_LANG_DIR = Path(__file__).resolve().parent.parent.parent / "content" / "languages"

# ───────────────────────────────────────────────────────────────────
# Built-in speech styles (fallback if JSON files missing)
# ───────────────────────────────────────────────────────────────────
SPEECH_STYLES: list[str] = [
    "formal",
    "noir",
    "pirate",
    "western",
    "genz",
    "robotic",
    "halting",
    "victorian",
    "shakespearean",
    "slang",
]

_BUILTIN_PROMPTS: dict[str, str] = {
    "formal": (
        "Speak in a formal, precise register. Use complete sentences, "
        "avoid contractions, and address others with titles."
    ),
    "noir": (
        "Speak like a hard-boiled detective narrator. Short clipped sentences, "
        "metaphors about rain and shadows, world-weary tone."
    ),
    "pirate": (
        "Arr, speak like a salty sea pirate. Use nautical terms, drop g's, "
        "say 'ye' instead of 'you', and sprinkle in 'matey' and 'arr'."
    ),
    "western": (
        "Speak with a frontier drawl. Use 'reckon', 'ain't', 'partner', "
        "and plain-spoken wisdom. Keep it laconic."
    ),
    "genz": (
        "Use modern Gen-Z slang naturally. 'no cap', 'fr fr', 'lowkey', "
        "'it's giving', 'slay', 'vibe'. Don't overdo it."
    ),
    "robotic": (
        "Speak in a flat, monotone, literal manner. No contractions, "
        "precise vocabulary, occasional technical jargon. Minimal emotion."
    ),
    "halting": (
        "Speak with hesitation — frequent pauses, ellipses, self-corrections, "
        "'um', 'er', restarting sentences. Nervous or uncertain energy."
    ),
    "victorian": (
        "Speak in a refined Victorian manner. Elaborate phrasing, indirect "
        "address, 'one finds that…', 'I dare say', genteel vocabulary."
    ),
    "shakespearean": (
        "Speak in Early Modern English. Thee/thou/thy, hath/doth, "
        "'prithee', inverted syntax, iambic flourishes when dramatic."
    ),
    "slang": (
        "Use street slang and colloquialisms. Keep it casual and punchy, "
        "with creative metaphors and shortened words."
    ),
}


def _load_style_from_json(style: str) -> str | None:
    """Try to load a speech style prompt from content/languages/<style>.json."""
    path = _CONTENT_LANG_DIR / f"{style}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("prompt", data.get("description", ""))
    except (json.JSONDecodeError, OSError):
        return None


def get_speech_style_prompt(style: str) -> str:
    """
    Return the system prompt string for a given speech style.

    Checks JSON files first, then falls back to built-in prompts.
    Returns empty string for unknown styles.
    """
    s = style.strip().lower()

    # Try JSON file
    json_prompt = _load_style_from_json(s)
    if json_prompt:
        return json_prompt

    # Built-in fallback
    return _BUILTIN_PROMPTS.get(s, "")
