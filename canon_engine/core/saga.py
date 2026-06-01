"""
Canon Engine — Saga System

Grand narrative framework with phases, beats, and pod hooks.
Provides the backbone structure for AI-driven storytelling.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# ── Content loader ────────────────────────────────────────────────────

_CONTENT_DIR = Path(os.environ.get(
    "CANON_CONTENT_DIR",
    Path(__file__).resolve().parents[2] / "content",
))


def _load_json(name: str) -> dict:
    p = _CONTENT_DIR / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


# ── Saga corpus ───────────────────────────────────────────────────────

def load_saga_corpus() -> dict:
    """Load saga seed data from content/narrative/saga_seed.json."""
    return _load_json("narrative/saga_seed.json")


def _load_pod_quests() -> list[dict]:
    """Load pod quest hooks from content/narrative/pod_quests.json."""
    data = _load_json("narrative/pod_quests.json")
    return data.get("pod_quests", [])


# ── State management ──────────────────────────────────────────────────

def ensure_saga(state: dict[str, Any]) -> None:
    """Ensure saga state structure exists."""
    saga = state.setdefault("saga", {})
    saga.setdefault("current_phase", "arrival")
    saga.setdefault("phase_index", 0)
    saga.setdefault("beat_count", 0)
    saga.setdefault("flags", {})
    saga.setdefault("hints", [])
    saga.setdefault("history", [])


# ── Prompt block ──────────────────────────────────────────────────────

def build_saga_prompt_block(state: dict[str, Any]) -> str:
    """Build saga context for system prompt."""
    ensure_saga(state)
    corpus = load_saga_corpus()
    saga = state.get("saga", {})

    phases = corpus.get("saga_spine", {}).get("phases", [])
    current_id = saga.get("current_phase", "arrival")

    # Find current phase
    current_phase = None
    for phase in phases:
        if phase.get("id") == current_id:
            current_phase = phase
            break

    if current_phase is None:
        return "## Saga\nNo active saga phase."

    lines = [f"## Saga: {current_phase.get('name', current_id)}"]
    lines.append(f"Tone: {current_phase.get('tone', 'neutral')}")
    lines.append(f"Description: {current_phase.get('description', '')}")

    # Show available beats
    beats = current_phase.get("available_beats", [])
    if beats:
        lines.append("Available narrative beats:")
        for beat in beats:
            lines.append(f"  - {beat.get('name', '?')}: {beat.get('type', '?')} (weight {beat.get('weight', 1)})")

    # Show flags
    flags = saga.get("flags", {})
    if flags:
        flag_str = ", ".join(f"{k}={v}" for k, v in flags.items())
        lines.append(f"Active flags: {flag_str}")

    # Show hints
    hints = saga.get("hints", [])
    if hints:
        lines.append(f"Recent hints: {'; '.join(hints[-3:])}")

    return "\n".join(lines)


# ── Saga actions ──────────────────────────────────────────────────────

def saga_advance(state: dict[str, Any], data: dict) -> None:
    """Advance saga phase or set flags.

    data keys:
      - phase: str (optional) — advance to specific phase
      - flag: str (optional) — set a story flag
      - flag_value: any (optional) — value for the flag
      - beat: str (optional) — record a narrative beat
    """
    ensure_saga(state)
    saga = state["saga"]
    corpus = load_saga_corpus()
    phases = corpus.get("saga_spine", {}).get("phases", [])

    # Set flag
    flag = data.get("flag")
    if flag:
        saga["flags"][flag] = data.get("flag_value", True)

    # Record beat
    beat = data.get("beat")
    if beat:
        saga["beat_count"] = saga.get("beat_count", 0) + 1
        saga.setdefault("history", []).append({
            "phase": saga.get("current_phase"),
            "beat": beat,
            "turn": data.get("turn", 0),
        })

    # Advance phase
    target_phase = data.get("phase")
    if target_phase:
        phase_ids = [p.get("id") for p in phases]
        if target_phase in phase_ids:
            saga["current_phase"] = target_phase
            saga["phase_index"] = phase_ids.index(target_phase)
            saga.setdefault("history", []).append({
                "phase": target_phase,
                "beat": "phase_change",
                "turn": data.get("turn", 0),
            })
    else:
        # Auto-advance based on flags/triggers
        current_phase = None
        for phase in phases:
            if phase.get("id") == saga.get("current_phase"):
                current_phase = phase
                break

        if current_phase:
            triggers = current_phase.get("escalation_triggers", {})
            story_flag = triggers.get("story_flag")
            if story_flag and saga["flags"].get(story_flag):
                # Advance to next phase
                idx = saga.get("phase_index", 0)
                if idx + 1 < len(phases):
                    next_phase = phases[idx + 1]
                    saga["current_phase"] = next_phase["id"]
                    saga["phase_index"] = idx + 1
                    saga.setdefault("history", []).append({
                        "phase": next_phase["id"],
                        "beat": "auto_advance",
                        "turn": data.get("turn", 0),
                    })


def saga_hint(state: dict[str, Any], data: dict) -> None:
    """Add a narrative hint to the saga."""
    ensure_saga(state)
    hint = data.get("text", data.get("hint", ""))
    if hint:
        state["saga"].setdefault("hints", []).append(hint)
        # Keep only last 10 hints
        if len(state["saga"]["hints"]) > 10:
            state["saga"]["hints"] = state["saga"]["hints"][-10:]


# ── HUD / API ────────────────────────────────────────────────────────

def saga_layout_snapshot(state: dict[str, Any]) -> dict:
    """Return saga state for HUD display."""
    ensure_saga(state)
    corpus = load_saga_corpus()
    saga = state.get("saga", {})
    phases = corpus.get("saga_spine", {}).get("phases", [])

    current_id = saga.get("current_phase", "arrival")
    current_phase = None
    for phase in phases:
        if phase.get("id") == current_id:
            current_phase = phase
            break

    return {
        "current_phase": current_id,
        "phase_name": current_phase.get("name", current_id) if current_phase else current_id,
        "phase_index": saga.get("phase_index", 0),
        "total_phases": len(phases),
        "beat_count": saga.get("beat_count", 0),
        "flags": dict(saga.get("flags", {})),
        "hints": list(saga.get("hints", [])),
        "tone": current_phase.get("tone", "") if current_phase else "",
        "available_beats": [
            {"name": b.get("name"), "type": b.get("type")}
            for b in (current_phase.get("available_beats", []) if current_phase else [])
        ],
    }


# ── Pod hooks ─────────────────────────────────────────────────────────

def process_saga_pod_hooks(state: dict[str, Any], turn: int) -> list[str]:
    """Check pod quest hooks against current saga flags and phase.

    Returns list of log lines for triggered events.
    """
    ensure_saga(state)
    saga = state.get("saga", {})
    current_phase = saga.get("current_phase", "arrival")
    flags = saga.get("flags", {})

    pods = _load_pod_quests()
    triggered: list[str] = []

    for pod in pods:
        pod_id = pod.get("id", "")
        pod_phases = pod.get("phases", [])

        # Check if pod is relevant to current phase
        if current_phase not in pod_phases:
            continue

        # Check if already triggered
        if saga.get("flags", {}).get(f"pod_{pod_id}_triggered"):
            continue

        # Simple flag-based trigger check
        hook = pod.get("hook", "")
        triggered.append(f"[SAGA] Pod quest available: {pod.get('name', pod_id)} — {hook}")
        saga["flags"][f"pod_{pod_id}_triggered"] = True
        saga.setdefault("history", []).append({
            "phase": current_phase,
            "beat": f"pod_triggered:{pod_id}",
            "turn": turn,
        })

    return triggered
