## 🛣️ ROADMAP (live document — update as you go)

**Where we actually are:** **`v0.5.2-j1`** · **Juncture 1** — localhost **web UI** shell talking to Python over **`localhost` FastAPI**, not a boxed “finish v0.1 then v0.2” Cursor Plan. Work order **deviated on purpose**: ship playable bridge + CRPG UX, keep engine depth growing in parallel. Source of truth for what landed when: **`canonchanges.md`**.

---

### Product direction

- **Python:** local JSON/session engine (**`POST /action`**, **`/health`**, handbook topics, same **`step_session_turn`** spine as terminal harness).
- **Web UI:** primary player-facing shell (`canon_engine.md` § HTTP bridge); terminal is dev/QA.
- **Version tag:** **`j1`** = **Juncture 1** web HUD milestone (menus, HUD, settings, banners, saves UX). Engine feature cut is **~v0.5.2** (quests layered on procedural world / NPC economy work — see changelog).

---

### In the repo today (rollup)

Rough checklist of **major capability already present** (not exhaustive):

| Area | Status |
|------|--------|
| Slash parser + demo session pipe | ✅ Rich command set incl. **`/quests`**, travel, NPCs, crafting, factions, combat, death/soul pipeline (see **`canon_engine.md`** + parser) |
| Saves | ✅ **`saves/<slot>.json`**, **`save_version`**, client manage/copy/delete + import/export |
| Procedural seeds · **`/world`** / **`/map`** | ✅ **`core/worldgen.py`** stack |
| NPCs, relationships, merchant pricing hooks | ✅ |
| Dynamic quests | ✅ **`core/quests.py`**, templates, turn-in hooks |
| Chroma cold paths | ✅ Optional tiers; narrator/HUD can gate vector block |
| Web HUD | ✅ Layout sync, LINK, shortcuts, pause, handbook scene |
| Web settings | ✅ Sections, **`client_prefs`** → session, autosave knobs, keybinds |
| Tests | ✅ Large **`tests/`** suite (run **`pytest`** before claiming done) |

---

### Backlog — next wins ( unordered; pick what the game needs )

These replace the old “v0.2 / v0.4 … ladder” as **Cursor Plan‑agnostic** buckets:

- **Setting & lore tools:** Setting selector / collision fantasy; bible auto‑population; richer backstory gen.
- **Companions & items:** Recruitment / loyalty; item lore cards + rarity presentation in HUD.
- **Combat UX:** Combat loop polish in the web client (**dice** line already optional via settings); escape/flee confirmations wired end‑to‑end if desired.
- **Economy depth:** Shops as scenes + tuned loops (price UI, stock stories) beyond current merchant math.
- **Admin / author:** **`/admin`**, **`/retcon`**, protected tooling.
- **Voice library:** **`content/languages/*.json`** speech packs per `.cursorrules` (not shipped as files yet — engine hooks exist via **`speech_style`**).
- **Art / vfx layer:** Portrait grid, scripted map scene, optional generative backdrop — **after** HUD contract feels stable.

---

### 🖼️ Later presentation

- Landscape / portrait art APIs
- Full-screen map beyond layout minimap snippet

---

## 🚨 NON-NEGOTIABLES

1. **No subscription wrappers** — direct API keys only.
2. **Lore consistency > clever output.** Drift from world bible = bug.
3. **Player agency is sacred.** Never auto-decide for the player.
4. **Admin mode is god mode** when engaged.
5. **No filler code.**
6. **Save discipline.** Autosave + interval from HUD (**`client_prefs`**), tutorial guards, explicit **`/save`** + export paths.

---

## 📝 NOTES

- **Cursor Plan** ≠ release order. Treat this file + **`canonchanges.md`** as the narrative of what shipped.
- Garros + crypt skeleton remain canonical QA faces.
- If you need semver for support, say **engine ~v0.5.2** + **client juncture** (e.g. **`‑j1`**) until a single bumped version exists alongside **`api_version`**.
