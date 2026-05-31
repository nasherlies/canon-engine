# Narrative saga framework — design law

This document is **canon for long-arc storytelling** in Canon Engine: how the engine encodes a **spine** (macro phases), **pods** (regional formula loops), and **consequences** that resurface across time. It complements `canon_engine.md` (game law and HTTP bridge). The **world bible** and **lore system** remain higher authority than anything here; the saga layer only **structures** pressure and hooks.

---

## Spine vs pods

- **Spine** — A small ordered list of **global saga phases** (e.g. arrival → rising pressure → convergence → reckoning → hook forward). Each phase has a **narrative goal** and **tone pressure**. Phases are **soft gates**: the player is never forced through a single script.
- **Pods** — **Regional or chapter-scale** cycles that repeat the same **macro-loop** in different places. A pod is where the **five-beat formula** runs; the spine tells you *where you are* in the larger arc.

Machine-readable defaults live in `content/narrative/saga_seed.json`. Runtime state lives under `state["saga"]` (see `core/saga.py`).

---

## Macro-loop (five beats)

Each pod should be navigable through this loop (names are author-facing; narration stays diegetic):

1. **Land** — Arrive, sense geography, factions, and threat **texture** without solving the arc.
2. **Wedge** — Ally or enemy **pressure** intensifies; a choice or betrayal surface that cannot be undone silently.
3. **Interconnect** — Earlier **world_flags**, bonds, nemeses, and region outcomes **Echo** into new scenes (DCs, prices, ambushes, offers).
4. **Liberate or destroy** — The regional threat resolves **according to player path** — not a single predetermined morality.
5. **Hook** — A **durably named** consequence and a clear **forward thread** without invalidating prior facts.

Echo **prior flags** when they naturally tighten or relieve tension — never as a lore retcon unless `/admin` allows it.

---

## Interconnection

- **Plot clocks** — Use `minutes_passed`, travel, and existing world time so pressure can build off-screen.
- **Relationship / faction** — `bond_*`, faction reputation, and `nemesis_*` seeds (via `npc_dispositions` and flags) should **change offers and risk**, not just dialogue flavor.
- **World flags** — Prefer **stable prefixes** so the model and operators can grep saves: `saga_`, `pod_`, `bond_`, `nemesis_`, `region_` (see `saga_seed.json`).

Early beats should set **specific, reusable** flags so later beats can **call them back** as mechanics (access, cost, DC bias) — not only as prose references.

---

## Player agency

- Saga phases and pods are **directives for the narrator**, not a railroad. **Branching inside a pod** is expected.
- **Soft gates** — Difficulty, prices, and who shows up can reflect phase/pod; **hard locks** that remove all options conflict with engine philosophy unless the table explicitly designs them.
- The **player always decides** meaningful choices; the model proposes, **Python applies** validated `state_updates`.

---

## `state_updates` contract

Reuse existing keys whenever possible:

- **Durable hooks** — `world_flags` with the saga prefix conventions above.
- **Quests** — Offer and progress through the existing quest system; optional **pod hooks** in `content/narrative/pod_quests.json` append `events` lines when flags become true (see `core/saga.py`).
- **Spine/pod movement** — `state_updates.saga_advance` (and optionally `saga_hint` as an alias the engine treats the same) with **only** whitelisted `phase_id` / `pod_id` from `saga_seed.json`, plus optional `register_echo` (short string stored in `saga.echo_flags`). Unknown IDs are **rejected** and logged; they do not crash the session.

---

## Operational rules

- When uncertain about a **fact**, **query lore** / world bible context as already required in `.cursorrules` — do not improvise contradictory canon.
- The **Narrator** receives a clipped **SAGA_FRAMEWORK** block built from corpus + live saga-relevant flags (`core/narrator.py`).
- Python remains the single **mutator** of authoritative state after narration (`narrator_apply`).

---

## File map

| Artifact | Role |
|----------|------|
| `content/narrative/saga_seed.json` | Spine, pods, consequence guide, flag patterns |
| `content/narrative/pod_quests.json` | Optional flag → `events` hook lines |
| `core/saga.py` | Load corpus, `ensure_saga`, prompt block, advance validation, layout snapshot, hooks |
