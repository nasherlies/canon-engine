# Canon Engine — Changelog (layman's terms)

Use this file to track what changed, in plain language.

## Color legend

- **GREEN (added):** New stuff that did not exist before.
- **YELLOW (changed):** Something that already existed was modified or improved.
- **RED (removed):** Something was deleted or no longer supported.

---

## Hotfix — assets 404, phantom combat/tutorial HUD, stuck “thinking”, slash palette (May 2026)

- **YELLOW · `api/server.py`:** Layout JSON now omits ``player.portrait_path`` when the file does not exist under ``assets/`` on disk (presets still carry ``res://assets/...`` paths even when no JPG is shipped). Stops the DevTools 404 spam and reliance on ``img.onerror``.
- **YELLOW · `web/modules/combat_hud.js`:** Phantom bout detection no longer requires ``combat_player_hp_max === 0`` — that prevented hiding when combat leaked ``active`` with real HP but zero enemies (exact screenshot case).
- **YELLOW · `web/modules/tutorial.js`:** Dash / em-dash–only titles count as empty so orphan tutorial shells hide.
- **GREEN · `web/modules/api.js`:** All ``fetch`` calls use ``AbortController`` with a **240s** ceiling — hung narrator requests clear ``busy`` / “thinking” instead of wedging the HUD forever.
- **YELLOW · `web/styles.css`:** Spinner uses explicit ``from/to`` rotation + ``inline-block`` + ``will-change`` for Opera GX / Chromium quirks.
- **YELLOW · `web/modules/store.js` + `command_palette.js`:** Slash palette wires once and **re-attempts when entering the game screen** so listeners always attach.

---

## CONTINUE + `/saves` — resume your last session from the main menu (May 2026)

> Operator wanted to pick up where they left off after closing the browser.

Saves already lived on disk as flat JSON under `saves/<slot>.json` — the engine had `/save`, `/load`, `/quicksave`, and autosave — but the web client's **CONTINUE** button was still labeled "coming soon" and did nothing.

- **GREEN (added) · `GET /saves`:** Lists every `*.json` in `saves/`, sorted by **last modified** (newest first). Each row includes `id` (slot name), `hero` (player name from the file), `turn`, `location`, `mtime`, `bytes`.
- **GREEN (added) · `web/modules/save_menu.js`:** On menu load and whenever you return to the main menu, fetches `/saves` and **enables CONTINUE** when at least one save exists. The subtitle under CONTINUE shows who / which slot / turn you'll resume.
- **GREEN (added) · `loadSaveSlot` in `web/modules/session.js`:** POSTs `/action` with `/load <slot>` for the newest file, clears the log, and lands you in the game HUD. Also calls `refreshSaveMenu()` after `/quit` so the menu shows fresh slots.
- **YELLOW (changed) · `web/index.html`:** CONTINUE placeholder text is now "Checking saves…" until the first fetch completes.
- **YELLOW (changed) · `content/manual/manual.json`:** New "Saving & Loading" topic + Getting Started line about CONTINUE.
- **Suite total:** **33** `test_api_server` cases (new `test_get_saves_lists_slot_files`).

---

## NEW GAME — BUILD YOUR OWN HERO + CHOOSE WORLD (genre · collision · starting location) (May 2026)

> Operator: *"cant forget, where is the create character features when i start a new game, with location selection"*

The full custom-character builder and world/setting picker the master spec called for, built end-to-end. Both presets AND custom heroes now route through CHOOSE WORLD on their way to /start_character, so every campaign starts with an explicit genre and starting location instead of silently inheriting whatever the preset implied.

- **GREEN (added) · `content/starting_locations.json`:** Four curated starting-location cards per genre (medieval_fantasy → Broken Crypt / Wayward Tavern / King's Road / Siege Camp; space_opera → Trade Station / Derelict Cruiser / Border Outpost / Freighter Bridge; gothic_horror → Blackthorn Manor / Saltburn Pier / St. Eldric's / Crossroads Chapel; western → Dust Bowl Town / Mesa Camp / Stagecoach Stop / Border Canyon; anime_dramatic → Academy Courtyard / School Rooftop / Tournament Hall / Cliffside Shrine). Each card carries an id, display label, one-line blurb, and tag list — surfaced as click-cards on the CHOOSE WORLD screen. The CUSTOM tile lets the player type any free-text anchor (supermarket, WW2 trench, magical academy) and that text feeds straight into the world seed.

- **GREEN (added) · `GET /world_settings`:** New read-only endpoint in `api/server.py`. Returns `settings` (every genre from `content/settings_catalog.json` annotated with `id`, `label`, `tone`, `speech_default`, plus its curated locations from `starting_locations.json`) and `speech_styles` (auto-discovered from `content/languages/*.json` so the dropdown picks up new languages without code changes — adds plain `formal` even though no JSON exists for it because Aria-style presets default to it). The CHOOSE WORLD and CREATE HERO screens hit this once and cache; no genre/location/speech-style strings are hardcoded in the client.

- **GREEN (added) · CREATE HERO screen (`web/index.html#screen-create-hero` + `web/modules/create_hero.js`):** The custom hero builder. Four input groups inside a CRPG-styled grid: **NAME** (text), **ARCHETYPE** (free text + datalist suggestions: knight, mage, ranger, rogue, detective, pirate, space ranger, samurai, alchemist, drifter, businessman, skeleton, bounty hunter, exile, scholar, medic), **SPEECH STYLE** (dropdown sourced from `/world_settings`), **STATS** (point-buy 60 across STR / DEX / INT / CHA / CON / LUCK with +/− buttons; pool counter goes red when over-spent and gold when under-spent; the NEXT button stays disabled until the spend exactly equals 60 and name + archetype are filled), and **BACKSTORY** (textarea + GENERATE WITH AI button that calls the existing `POST /backstory` endpoint and pastes a 3-6 sentence draft you can edit).

- **GREEN (added) · CHOOSE WORLD screen (`web/index.html#screen-choose-world` + `web/modules/choose_world.js`):** Three-step picker that runs for every campaign — preset OR custom. **Step 1 BASE GENRE:** five cards (one per setting in `settings_catalog.json`) showing tone + default speech style; clicking one re-renders the location grid. **Step 2 COLLISION (optional):** dropdown of the *other* genres — picks a secondary that bleeds into the primary (knight in space station, samurai in noir LA). Empty for a pure single-genre world. **Step 3 STARTING LOCATION:** four curated cards for the chosen genre + a CUSTOM tile that reveals a free-text input. The screen footer shows a live summary ("Space Opera × Gothic Horror at \"Frontier Trade Station\".") and the START ADVENTURE button stays disabled until both genre and location are set.

- **YELLOW (changed) · `web/modules/character_select.js` adds BUILD YOUR OWN tile:** First card on the SELECT HERO grid is now a dashed-border "BUILD YOUR OWN" tile with a `+` glyph that emits `ce:open-create-hero`. Selecting any preset card no longer starts the campaign immediately — it just enables the NEXT button, which routes to CHOOSE WORLD. Power flow stays one-click for impatient players: BUILD YOUR OWN → CREATE HERO → CHOOSE WORLD → START. Preset flow is two clicks: pick card → NEXT → pick world → START.

- **YELLOW (changed) · `web/modules/session.js` `startCharacter(character)` now takes the assembled payload:** Old signature was `startCharacter(preset)` and the function quietly stripped `portrait_url`. New signature accepts the fully-assembled character blob from CHOOSE WORLD: preset body OR custom builder body, plus `setting_primary`, `setting_secondary`, `world_seed`, `starting_location`. Engine `/start_character` already tolerated extra keys, so passing the whole blob is forward-safe. Also dropped the post-start auto-`/look` because the intro narration covers it (and the `/look` button still works whenever the player wants).

- **YELLOW (changed) · `web/app.js` wires the two new screens:** Imports `openCreateHero`/`wireCreateHero` and `openChooseWorld`/`wireChooseWorld`. Adds two action handlers (`back-to-character` and `back-from-world`) for the BACK arrows, and listens for `ce:open-create-hero` / `ce:open-choose-world` window events emitted by the character_select tile and the create_hero NEXT button respectively. The existing NEXT button on SELECT HERO routes to either CREATE HERO or CHOOSE WORLD based on `store.customHeroChosen`.

- **GREEN (added) · `web/modules/store.js` new fields:** `customHero` (assembled blob from CREATE HERO), `customHeroChosen` (flag), `worldChoice` (assembled blob from CHOOSE WORLD: `primary`, `secondary`, `location_id`, `location_text`).

- **GREEN (added) · `web/styles.css` ~250 lines of CRPG-themed styling:** New rules for `.preset-card-custom` (dashed gold border + gradient), `.builder-shell` / `.builder-input` / `.builder-textarea` / `.stat-grid` / `.stat-row` / `.stat-btn` (CREATE HERO), and `.world-shell` / `.world-card` / `.world-location-card` (CHOOSE WORLD). Responsive `auto-fit` grids, gold-glow on selection, dashed border on the CUSTOM tiles. Matches the existing dark-amber palette (`--bg-0`, `--gold`, `--fg-mute`).

- **GREEN (added) · `tests/test_api_server.py` two new regression tests:**
    - `test_world_settings_returns_genres_locations_and_speech` — asserts `/world_settings` returns all five canonical genres, that medieval_fantasy carries at least one curated location card with `id` / `label` / `blurb`, and that the speech-style list includes `noir`, `pirate`, `western` (proves the `content/languages/*.json` auto-discovery works).
    - `test_start_character_honors_setting_primary_and_secondary` — posts a full character payload with `setting_primary: "space_opera"` + `setting_secondary: "western"`, then reads the live `app.state.session.world_flags` directly to assert both fields round-trip into the engine. Also re-verifies the full-HP regression (`hp == hp_max > 1`).

- **YELLOW (changed) · `content/manual/manual.json` two new player-manual topics:**
    - **BUILD YOUR OWN — Custom Hero Builder** — explains every input on CREATE HERO, the 60-point stat pool, and the AI backstory button.
    - **CHOOSE WORLD — Genre, Collision & Starting Location** — explains the three steps, the optional collision blend, the curated cards vs. CUSTOM free-text, and how the picker anchors worldgen.
    - Updated the `getting_started` topic to mention BUILD YOUR OWN and the world picker.

- **Suite total:** **371 passing** (was 369 — 2 new API tests, 0 regressions).

- **Live verification:** End-to-end probe (`_e2e_probe.ps1`):
    - `/world_settings` returned 5 genres × 4 locations + 10 speech styles. ✓
    - Custom hero "Vex Talon" (bounty hunter / noir / custom 60-point stat spread) booted into `space_opera × gothic_horror` at "Frontier Trade Station" — full HP (110/110), no tutorial leak, no combat leak. ✓
    - `/look` narration reads "Industrial steel and fractured cryo-crystal lined the damp walls, creating a hum of echoing footfalls and whispers that lingered like ghos…" — confirming the `setting_primary` + `setting_secondary` blend reached the AI worldgen layer. ✓

---

## Hotfix — NEW CAMPAIGN unsticks combat + tutorial, /look talks back, presets spawn at full HP (May 2026)

> Operator: *"started a campaign, 4 problems, did the look button didnt get a response (dont fix this, fix the command), why is the combat interface open with no '/fight' push, its processing the campaign i started as the tutorial, like what?, why when its a preset, they start with 1HP?"*

Four bugs reported, one shared root cause for three of them. Layered, surgical fixes — no design changes.

- **YELLOW (changed) · `ui/game_session.py` combat shell now lets `/start_character` through:** The big one. The combat-shell gate (`if combat_active_full(state): if kind not in _COMBAT_SHELL_KINDS: ...`) was rejecting `/start_character` whenever ANY combat was live in the in-memory session — including leftover combat from a tutorial round, a previous campaign turn, or a dev-warp boot blob. The handler quietly appended `[COMBAT] Finish the duel ...` to the log and returned without ever calling `build_character_session_state`, so the player's NEW CAMPAIGN click did nothing: tutorial card stayed up, combat HUD stayed up, the old hero stayed loaded. Added `start_character` to `_COMBAT_SHELL_KINDS` with an inline comment explaining the meta-command rule (these REPLACE the whole session and must never be blocked by in-bout gates). This single change resolves three of the four reported issues — phantom tutorial, phantom combat, and "campaign processed as tutorial".
- **YELLOW (changed) · `ui/game_session.py` `/look` (`look_around`) now produces narration:** `look_around` previously appended `[LOOK] {location}` plus indented minimap sub-lines to `command_log` and returned `(_RC_OK, None, None)` — no narration. The web client's chat filter only echoes a small set of bracketed system tags (`SYSTEM|ERROR|HANDBOOK|JOURNAL|TUTORIAL|SKILL|INV|CHECK|SHOP`) AND only checks the *last* line of the tail, which after `/look` is an indented sub-line that matches nothing. Result: the LOOK button appeared dead. Per operator instruction (*"don't fix this, fix the command"*), `/look` now routes through `narrate_and_apply` with a synthesized `/do Look around carefully ...` prompt so the AI describes the scene cinematically. Power users still get the structured `[LOOK]` log lines for debugging. A local fallback synthesizes a sentence from the minimap when the narrator stalls (e.g. no API key, model refusal) so the player never gets a blank reply.
- **YELLOW (changed) · `core/character_session.py` presets spawn at full HP:** The seed dict hardcoded `"hp": 1` (legacy from the demo skeleton). `recalculate_stats(out)` only **clamps** existing HP to the new ceiling — it never tops up — so Marshall, Garros, and every other preset opened the campaign at literally 1 HP no matter how many CON points they were rolled with. Fixed two ways: seed dict now starts at `hp: 100`, and after `recalculate_stats(out)` we explicitly pin `out["player"]["hp"] = out["player"]["hp_max"]` so a high-CON hero still opens at the new (raised) ceiling rather than a stale 100.
- **YELLOW (changed) · `core/character_session.py` defensive reset of `combat` and `tutorial`:** Belt-and-suspenders in case a future code path resurrects state across `/start_character` (or a save migration drops a stale flag in). `build_character_session_state` now always pins `out["combat"] = {"active": False}` and `out["tutorial"]["active"] = False` before returning. `step_session_turn`'s `state.clear() + state.update(new_state)` already wipes combat/tutorial in practice, but pinning them explicitly means the layout never reports a phantom fight or tutorial step on character creation, even if some future feature snuck a key past `state.clear()`.
- **GREEN (added) · `tests/test_game_session.py` regression coverage:**
    - `test_start_character_spawns_at_full_hp` — seeds a new hero, asserts `player.hp == player.hp_max > 1`.
    - `test_start_character_clears_combat_and_tutorial` — pre-seeds the session with `combat.active = True` AND `tutorial.active = True`, fires `/start_character`, asserts both flags are False after — directly catching the original combat-shell-gate regression.
    - `test_look_returns_player_visible_narration` — fires `/look`, asserts non-empty narration is returned and `[LOOK]` lines still land in `command_log`.
- **Suite total:** **369 passing** (was 366 — 3 new tests, 0 regressions).
- **Operator note:** `.env` ships with `CANON_ENGINE_DEV=1`, which loads `dev_warp.example.json` (Warp Mage prefab + dev `/godmode`/`/spawn`) at boot AND on every `/quit`. Set it to `0` (or delete the line) for a vanilla campaign experience. Engine fixes above hold either way — the combat-shell gate was the underlying issue, not dev mode.

---

## Quest Log — narrator-driven free-text quests, paired with the Codex (May 2026)

> Operator: *"Quest Log into the HUD sidebar. Quests are discovered dynamically through the narrator's JSON response and tracked in real-time. ACTIVE / COMPLETED / FAILED collapsible sections, checklist objectives, NEW QUEST / QUEST COMPLETE / QUEST FAILED toasts. Wire the two systems together so completing a quest can unlock a related Lore Card."*

Canon Engine already had a typed-objective procedural quest system (`hunt 3 wolves`, `deliver 5 ore`, `travel_to`, `reveal_lore`) that lives in `state.world.quests` and is offered by procedural NPCs via `/accept`. The user's spec was a *different shape* — free-text narrator-driven quests with checkbox objectives the AI manually flips. **Both shapes now coexist** in the same storage; narrator quests carry a `source: "narrator"` tag and a `type: "narrative"` marker on every objective so the older typed helpers gracefully skip them.

- **GREEN (added) · `core/narrator_quests.py`:** New module with the full narrator-quest contract:
    - `apply_quest_update_payload(state, updates, *, turn)` — reads `state_updates.quest_update` (single dict) AND `state_updates.quest_update_many` (list), caps at **3 updates/turn** to prevent runaway drift. Validates and dispatches to four handlers:
        - `_handle_new_quest` — slugifies the id (idempotent `nq_<slug>` even when the model re-uses a previous canonical id), normalizes objectives (clamped to 1-8 entries, free text, `completed: bool`), stores under `state['world']['quests']['active'][qid]` with the `narrative` objective type so engine typed helpers ignore it.
        - `_handle_objective_complete` — finds by `objective_index` (0-based) OR `objective_text` (case-insensitive exact match), flips `completed: true`, no-op if already done.
        - `_handle_quest_complete` — flips status, archives the closed quest in `state['world']['narrator_quest_archive']['completed']`, removes from active, ALSO calls the Lore Codex link helper.
        - `_handle_quest_fail` — same archival path under `failed`, never crashes if the id is unknown.
    - `narrator_quests_prompt_block(state, max_chars=700)` — compact text snapshot for the system prompt with ACTIVE titles, per-quest TODO objectives, and `COMPLETED_IDS` / `FAILED_IDS` lists. The instruction line at the end says *"Do NOT re-issue completed/failed ids; advance ACTIVE objectives when fiction warrants."*
    - `quest_log_payload(state)` — full `{active, completed, failed, counts}` blob shaped for the web UI, with each card carrying `id, title, giver, description, objectives, status, discovered_at, source`.
    - `drain_quest_pulse(state)` — read+clear the per-turn event list (matches the Codex pulse pattern).
    - **Quest ↔ Codex link** (the user's headline pairing ask) lives in `_maybe_link_codex`. If the narrator named an explicit `lore_unlock` (object with `title/category/description`), the engine routes it through `discover_card`. Otherwise, when a quest closes with a non-empty `giver`, the engine **auto-promotes the giver to a Character lore card** unless one already exists — giving every closed quest at least one codex artifact for free.
    - **Circular-import guard:** `core.quests` chains back to `core.narrator` via `recovery → narrator`, so this module lazy-imports `ensure_quests` inside a private helper rather than at module scope. Documented inline.
- **GREEN (added) · narrator JSON contract extended:** `core/narrator.py` `_JSON_INSTRUCTION` now teaches the model `quest_update` / `quest_update_many` with full per-action requirements (`new_quest` needs title + 1-6 objectives; `quest_complete` may carry `lore_unlock`; etc.), explicit guidance to issue at most one `new_quest` per beat, and the rule against re-issuing closed ids.
- **GREEN (added) · system-prompt injection:** `_build_system_prompt` now splices `narrator_quests_prompt_block(state)` between the `SAGA_FRAMEWORK` block and the player block. The model sees current ACTIVE quests with TODO objectives every turn — no extra API call required.
- **GREEN (added) · opening-scene seed nudge:** `_INTRO_INSTRUCTION` now ends with an OPTIONAL clause asking the model to seed exactly one starter `quest_update` if a clean hook fits the hero's archetype + setting (missing person for a detective, salvage rumor for a pirate, system-glyph errand for a leveling-system protagonist). The instruction explicitly says *"Skip entirely if uncertain"* — no forced quest spam.
- **GREEN (added) · `narrator_apply` route:** `core/narrator_apply.py` now imports `apply_quest_update_payload` and calls it right after the lore-codex apply, appending each `[QUEST]` log line into `command_log`. Python remains the only path that mutates quest state — the model proposes, the engine disposes.
- **GREEN (added) · `GET /quests` endpoint:** `api/server.py` exposes the full active/completed/failed buckets + counts. Engine typed quests still live behind `/journal` (slash-command access via `/quests`, `/quest <id>`, `/accept`, `/turnin`, `/abandon` is unchanged).
- **GREEN (added) · `layout.quests` HUD block:** Every `/action` response carries `layout.quests = {active: [top-3 cards], active_full_count, counts: {active, completed, failed}, pulse: [{kind, id, title, ...}, ...]}`. The pulse drains after read so events toast exactly once. The topbar QUESTS button has a green pip showing the active count.
- **GREEN (added) · QUESTS overlay (web):** `web/modules/quests_overlay.js` — top-bar button between CODEX and JOURNAL. Modal has three collapsible sections: ACTIVE (gold, expanded by default), COMPLETED (green, collapsed; objectives strike through), FAILED (red, collapsed; objectives crossed out with ✗). Each card shows title (gold serif), giver (smaller mono caps), description (parchment paragraph), and a checklist of objectives with ✓/·/✗ marks per state.
- **GREEN (added) · sidebar QUESTS glance:** `web/modules/sidebar.js` renders a new HUD section under VITALS/STATS/INVENTORY when at least one narrator quest is active. Shows `QUESTS (N)`, an inline OPEN button, and the top three active titles with their `done/total` objective progress. Clicking the section's OPEN button (or the topbar button) jumps into the full reader.
- **GREEN (added) · pulse toasts:** `web/modules/session.js` reads `layout.quests.pulse` and fires:
    - **`NEW QUEST: <title>`** (gold/ok) — for `kind: "new"`
    - **`QUEST COMPLETE: <title>`** (gold/ok) — for `kind: "complete"` (a follow-up *Lore Discovered* toast can fire on the same beat if a Codex card was auto-linked)
    - **`QUEST FAILED: <title>`** (red/error) — for `kind: "fail"`
    - silent `[QUEST] Progress: <objective>` system-log line — for `kind: "progress"` (no toast — quiet ticks aren't worth a popup)
    - capped at 3 toasts per beat to avoid burying the player when the model batches updates.
- **GREEN (added) · `Quest Log` topic in player manual:** `content/manual/manual.json` adds a "QUESTS — ACTIVE / COMPLETED / FAILED" entry covering the sidebar glance, the three-section reader, how the narrator issues quests, the Codex link on completion, and the relationship between narrator quests (auto-closed by story) and the older typed procedural quests (closed via `/turnin`).
- **GREEN (added) · QUEST styling:** `web/styles.css` adds parchment-flavoured `.quest-card` with status-coloured borders (gold for ACTIVE, mossy green for COMPLETED, blood red for FAILED), checklist with ✓ marks (green), ✗ marks for failed, strike-through on closed, and a dim `.quest-glance-row` for the sidebar glance.
- **GREEN (added) · `tests/test_narrator_quests.py`:** 17 new tests covering: new-quest creation + dedupe by id + objective normalization, the 3-per-turn cap, pulse emission, objective-complete by index AND by text match, unknown-id silent skip, no-double-pulse on re-completion, quest-complete archival + ledger update + pulse, **engine auto-promotes the giver to a Character codex card** when no `lore_unlock` is named, **explicit `lore_unlock` overrides the giver fallback**, fail archival, end-to-end through `apply_narrator_result`, and the prompt block format.
- **GREEN (added) · `tests/test_api_server.py` extensions:** `test_quests_endpoint_returns_buckets`, `test_layout_quests_block_present`. **Suite total: 366 passing** (was 347 — 19 new tests, 0 regressions).
- **YELLOW (changed) · `core/narrator.py` opening scene:** The intro instruction grew an OPTIONAL final clause about seeding one starter quest if a hook fits the hero. Tone-preserving — explicitly says skip if uncertain.

---

## Lore Codex — discoverable cards with semantic narrator integration (May 2026)

> Operator: *"Add a 'Lore Card' system (Codex) into the HUD. Collectible snippets about Characters, Locations, Factions, Items, History. 'Discovered' vs 'unknown' visual state. Look for a new key in the AI's JSON return called `discovered_lore`. Populate with common-knowledge cards based on the player's chosen World/Setting so the list isn't empty at the start."*

The spec was written for a generic JS state object; landing it inside Canon Engine meant routing the whole thing through the project's existing rule discipline — Python is the only state mutator, the narrator returns `state_updates`, and the engine validates + dedupes before anything is appended. The end result feels exactly like the spec asked for, but it stays inside the contract.

- **GREEN (added) · `core/lore_codex.py`:** New module with the full codex contract:
    - `slug_for(title, category)` — stable id (`category__title_slug`).
    - `normalize_card(raw, …)` — validates + clamps title/description, snaps category to one of `character|location|faction|item|history`, defaults source/discovery turn.
    - `ensure_codex(state)` — idempotent; back-compat for old saves with no `lore_cards` key.
    - `seed_initial_codex(state)` — reads `world_flags.setting_primary` (and `setting_secondary` if present), pulls common-knowledge cards from `content/lore/seed_lore.json`, falls back to a `_default` bucket.
    - `discover_card(state, raw, *, turn, source)` — appends if new, unlocks an existing locked seed card if found, pushes the id onto a transient `state['_lore_pulse']` list.
    - `apply_discovered_lore_payload(state, updates, *, turn)` — reads `state_updates.discovered_lore` (single object) AND `state_updates.discovered_lore_many` (list), caps at **4 cards/turn** to prevent runaway floods, returns `[LORE]` log lines.
    - `drain_pulse(state)` — read+clear the per-turn pulse so the API can surface "newly discovered this turn" without polling.
- **GREEN (added) · `content/lore/seed_lore.json`:** Common-knowledge cards keyed by setting:
    - **medieval_fantasy** — The Iron Duchy *(faction)*, The Long Road *(location)*, The Crypt-Bound Oath *(history)*.
    - **space_opera** — Titan Frontier Authority *(faction)*, The Dust Lanes *(location)*, Quietfire Incident '83 *(history)*.
    - **gothic_horror** — The Sanguine Sovereigns *(faction)*, The Pale Cathedral *(location)*, The Hollow Concord *(history)*.
    - **western** — Garros Fenchurch *(character)*, Dustfall County *(location)*, The Iron Ring *(faction)*.
    - **anime_dramatic** — The Quiet Glyph (LV. 1) *(item)*, The Underworld Below the Boardwalk *(location)*, The Awakened *(faction)*.
    - **_default** — The Threshold Realm *(location)*, The Saga Frame *(history)* — universal fallback.
- **GREEN (added) · narrator JSON contract extended:** `core/narrator.py` `_JSON_INSTRUCTION` now teaches the model an optional `discovered_lore` (object) / `discovered_lore_many` (array) field. The instruction explicitly says "ONLY emit when narration FIRST names a new entity worth recording (place, faction, recurring NPC, mythic item, recorded historical beat)" and warns against routine descriptive flavor. The engine still dedupes silently if the model over-emits.
- **GREEN (added) · `narrator_apply` route:** `core/narrator_apply.py` now imports `apply_discovered_lore_payload` and runs it right after `bible_entities` ingestion, appending each card via the validated path and emitting `[LORE] Discovered: <title> (<category>)` lines into the command log. **Python remains the only path that mutates `state['lore_cards']`** — the model proposes, the engine disposes.
- **GREEN (added) · session bootstrap seeding:** `core/character_session.py` calls `seed_initial_codex(out)` after the starting kit lands and before `recalculate_stats`. New saves get 2-3 setting-appropriate cards on turn 0 with a `[SYSTEM] Codex seeded with N common-knowledge card(s).` log line. Existing saves without a codex are seeded lazily by `ensure_codex` (empty list, no auto-seed — the world doesn't suddenly grow lore on a re-open).
- **GREEN (added) · `GET /codex` endpoint:** `api/server.py` exposes the full session card list, plus `by_category` grouping and `counts {total, discovered}`. Read-only — never mutates state.
- **GREEN (added) · `layout.codex` HUD block:** Every `/action` response now carries `layout.codex = {discovered, total, lore_pulse: [{id, title, category}…], recent: [last 3 ids]}`. The pulse list is **drained after read**, so a card pings exactly once. The HUD pip shows `discovered/total` next to the CODEX button.
- **GREEN (added) · CODEX button + overlay (web):** New top-bar button between STATS and JOURNAL with a small gold pip showing the discovery ratio. `web/modules/codex_overlay.js` opens a tabbed modal (**ALL · CHARACTERS · LOCATIONS · FACTIONS · ITEMS · HISTORY**). Each card renders as a parchment-style panel with a category badge, gold serif title, in-character body text, and a tiny "Discovered turn N · source" footer. Locked cards (engine-seeded but not yet revealed) render blurred with a `?` overlay and italic placeholder copy.
- **GREEN (added) · Lore Discovered toast:** `web/modules/session.js` reads `layout.codex.lore_pulse` after every action and fires a `Lore Discovered — CATEGORY · Title` toast (capped at 2 per turn so a chatty narrator can't bury the player), with a `+N more` summary toast if more than two arrived in the same beat. Each pulse also drops a `[LORE]` line into the system log.
- **YELLOW (changed) · CHARACTER → LORE tab repointed:** `web/modules/stats_overlay.js` LORE tab used to (mis-)read `/manual` (operator content). It now reads `/codex` and lists the discovered cards with category-prefixed titles, plus the recent-events strip. The dedicated CODEX overlay is the full reader; the LORE tab is the at-a-glance condensed version.
- **GREEN (added) · `Codex` topic in player manual:** `content/manual/manual.json` adds a "Codex — Discovered Lore" entry explaining seeding, semantic discovery, the locked/unlocked states, and the difference between the dedicated overlay and the in-overlay LORE tab. The `Stats, Skills & Lore` topic was updated so its LORE tab description matches the new behaviour.
- **GREEN (added) · CODEX styling:** `web/styles.css` adds parchment-flavoured `.codex-card`, per-category `.codex-cat-badge` colours (warm amber for character, mossy green for location, blood red for faction, gold for item, slate blue for history), a soft-glow `.codex-pip`, and a blurred `.codex-card.locked` state with a `?` glyph corner. CRT/vignette overlays still apply on top.
- **GREEN (added) · `tests/test_lore_codex.py`:** 17 new tests covering slug stability, title/description validation, seed-bucket coverage by setting, dedupe by id, locked-card unlock-on-discover, the per-turn cap of 4, narrator-apply integration end-to-end, and full `build_character_session_state` integration for Garros (medieval_fantasy bucket).
- **GREEN (added) · `tests/test_api_server.py` extensions:** `test_codex_endpoint_returns_cards_and_counts`, `test_layout_codex_block_present`, `test_codex_seeds_after_start_character`. **Suite total: 347 passing** (was 328).

---

## Genre-tagged starting kits — every hero spawns slot-appropriate (May 2026)

> Operator: *"follow-up authoring some genre-tagged starting items so each new hero comes with slot-appropriate gear"* — landed.

- **GREEN (added) · `content/presets/starting_kits.json`:** A new content file keyed by preset id. Each kit holds an `inventory` list (4–6 items per hero) and an `equip` map (canonical slot → item name). Items use the same shape the engine already validates (`name, rarity, qty, itype, weight, lore, equip_slot, consumable, effects, tags`) — no new schema, no new dependencies. Authored kits for all nine canon presets:
    - **Garros (medieval knight, western drawl)** — Dented longsword *(weapon_main)*, Patchwork plate vest *(chest_armor)*, Roadworn tunic *(chest_clothing)*, Dented knight's badge *(accessory_1)*, Trail rations ×3.
    - **Aria (court mage, formal speech)** — Engraved dagger *(weapon_main)*, Patched mage robe *(chest_clothing)*, Embered sigil *(accessory_1)*, Vial of inkpetal tea ×2 *(MP regen)*.
    - **Thal (renegade scholar)** — Knurled walking staff *(weapon_main)*, Ink-stained robe *(chest_clothing)*, Notebook of partial truths *(accessory_1)*, Midnight tonic *(MP regen)*.
    - **Kharvok (vampire orc, halting threats)** — Heat-cracked cleaver *(weapon_main, fire-tinged)*, Spiked pauldrons *(chest_armor)*, Iron-thread choker *(neck, ward)*, Blood-flask thrall vial ×2.
    - **Aegis-7 (1990s deity-marked construct)** — Service-issue sidearm *(weapon_main)*, Riveted alloy plate *(chest_armor)*, Deity-mark stencil patch *(accessory_1)*, Coolant cell ×2 *(stamina)*.
    - **Marshall Junior (1940s detective)** — Service revolver *(weapon_main)*, Rumpled trench coat *(back)*, Pressed white shirt *(chest_clothing)*, Grey wool fedora *(head)*, Press-pass notebook *(accessory_1)*, Field bandage pack ×2.
    - **Dare WestSea (sole young pirate)** — Salt-bitten cutlass *(weapon_main)*, Open-collared linen shirt *(chest_clothing)*, Frayed red bandana *(head)*, Father's brass compass *(accessory_1, story hook)*, Hardtack ration ×4.
    - **Lt. Keppo (Titan-born space ranger)** — Ranger sidearm *(weapon_main)*, Olive exo-jacket *(chest_armor)*, Pressurized helmet *(head)*, Ranger silver star *(neck, rank)*, Stim cartridge ×2.
    - **Sean "SB" Brooke (2000s skater w/ system glyph)** — Beat-up skateboard *(weapon_main, blunt/improvised)*, Oversized black hoodie *(chest_clothing)*, Backwards snapback *(head)*, Over-ear headphones *(neck)*, System-glyph pendant *(accessory_1, lore)*, Energy drink ×3.
- **GREEN (added) · `core/starting_kits.py`:** New tiny module that loads the kit file once (with a cache + a `reset_kits_cache` test hook), looks up a preset id, and exposes `apply_starting_kit(state, preset_id)`. Every authored item runs through `core.inventory.normalize_item` (so the existing item contract — id, effects shape, tags, qty/weight clamps — is enforced) before it lands in `state["inventory"]`. Pre-equip entries route through `resolve_equip_slot`, so kits can use either canonical slot keys (`weapon_main`) or the friendly aliases (`weapon`, `armor`, `shirt`, `cloak`, `hat`, `neck`, `accessory`, …) and still map onto the 17-slot taxonomy.
- **GREEN (added) · `build_character_session_state` hook:** **`core/character_session.py`** now calls `apply_starting_kit(out, character["id"])` once after `ensure_world` + `ensure_tutorial_state` and **before** `recalculate_stats`, so a hero's stats reflect their gear from turn zero. If the payload has no preset id (tutorial / freeform spawns) or the id has no kit, it skips silently. A `[SYSTEM] Starting kit applied — N item(s) in pack; equipped: …` line is appended to the command log so the dev console reflects what landed.
- **GREEN (added) · `tests/test_starting_kits.py`:** Ten new tests + 27 subtests cover the schema and the integration end-to-end:
    - File exists and parses; every preset id has a matching kit; every kit normalizes cleanly.
    - Every equipped slot key resolves to one of the seventeen canonical slots, and every named equip target exists in that kit's inventory.
    - Unknown / blank preset ids are no-ops (no crash, empty pack).
    - Garros's kit seeds the right slots and flips `equipped: True` on the right items.
    - Marshall Junior's preset boots a full session with revolver in `weapon_main` and trench coat in `back`.
    - A freeform character (no `id`) still boots cleanly with an empty pack.
    - Every authored preset boots a session without raising. **Suite total: 328 passing** (was 318).
- **YELLOW (changed) · player turn zero:** Heroes now spawn with slot-appropriate gear instead of an empty pack. The narrator can still introduce additional items mid-story; the kit is the floor, not the ceiling. No prompt or narration logic changed — gear shows up in `state["inventory"]`/`state["equipment"]` exactly as if the player had picked it up earlier.

---

## Manual + real combat HUD + 17-slot equipment + per-row item actions (May 2026)

> Operator: *"handbook should be alike to a user manual to how to play and use the features of the game not my changelog, also the combat window should have a HUD of its own, not terminal looking and with combat buttons too. Inventory screen should have use, combine and inspect, drop. For equipment we should have more slots for each body part (hands, neck, head, legs etc) too kinda like curios from minecraft, also armor slot should be separate from artifact/clothes slots."* — all four shipped in this batch.

- **GREEN (added) · player MANUAL:** **`content/manual/manual.json`** — eleven authored player-facing topics: Getting Started, Action Bar (SAY/DO/THINK), Slash Commands reference, Inventory (INV), Stats / Skills / Lore (STATS), Equipment (the 17-slot system), Combat HUD, Interactive Tutorial, Settings, Saving & Loading, About the World & Tone. **`GET /manual`** in **`api/server.py`** serves it. Top-bar button renamed **HANDBOOK → MANUAL**; opens a side-nav reader (**`web/modules/modals_misc.js`** `openManual`) — left rail = topic list, right pane = the topic body. STATS overlay's LORE tab now also reads `/manual` (player-facing context only). Operator changelog topics still live behind **`/handbook`** (slash-command access only) so release notes never leak into the player manual.
- **GREEN (added) · 17-slot Curios-style equipment:** **`core/inventory.py`** now defines **`EQUIP_SLOTS`** with seventeen layered slots:
    - **head**, **face**, **neck**, **back**
    - **chest_armor** + **chest_clothing** (armor and cloth layered separately)
    - **hands**, **waist**
    - **legs_armor** + **legs_clothing** (same dual-layer treatment)
    - **feet**
    - **ring_left** + **ring_right**
    - **weapon_main** + **weapon_off** (off-hand can hold a second weapon or a shield)
    - **accessory_1** + **accessory_2** (open curio slots)
  Backwards-compatible: **`ensure_equipment`** migrates the old 4-slot dict (`weapon`/`torso`/`accessory_*`) to the new keys on first read and strips the legacy keys, so existing saves keep working with no manual edits.
- **GREEN (added) · slot alias resolver:** **`resolve_equip_slot(token, eq)`** in **`core/inventory.py`** maps shorthand tags (`weapon`/`armor`/`shield`/`shirt`/`boots`/`gloves`/`pants`/`greaves`/`amulet`/`cloak`/`belt`/etc.) to canonical slot keys. **`ring`** auto-promotes to **`ring_left`** then **`ring_right`**; **`accessory`/`curio`** auto-promotes between curio_1 and curio_2. **`use_item`** + **`equip_suggest.upgrade_hint_line`** were rewritten to use the resolver — old item catalogs equip cleanly without touching their JSON.
- **GREEN (added) · `GET /equipment/slots`:** Canonical slot list + display labels (e.g. `CHEST · ARMOR`, `RING · L`) so the web body map renders the official order without hardcoding.
- **GREEN (added) · combat HUD panel:** **`web/modules/combat_hud.js`** — when `layout.combat_active` is true, a real combat panel takes over the center column (replaces the red terminal-style banner). Shows the round counter, player HP bar, an enemy roster (each enemy with its own HP bar; click a row to set the active target), companion HP bars, and six action buttons: **ATTACK / BLOCK / ITEM / LOOK / ORDER / FLEE**. ATTACK fires `/attack <index+1>` against the selected enemy (falls back to enemy #1 if no target picked). ITEM opens the inventory overlay so the player can pick a consumable. ORDER is hidden when no companion is in the fight.
- **GREEN (added) · per-row inventory actions:** **`web/modules/inventory_overlay.js`** — every item row in the ITEMS tab now has buttons for **USE / EQUIP / UNEQUIP** (label flips based on item state), **INSPECT**, **COMBINE** (with an inline picker when multiple combine partners are in the pack), and **DROP**. Drop on a Rare-or-better item asks twice — the button reads `CONFIRM DROP?` for ~4 seconds before the second click commits.
- **GREEN (added) · expanded body map:** New 17-rect SVG silhouette (head, face, neck, chest layered armor/cloth, back, hands, waist, legs layered, feet, two rings, two weapons, two curios). Filled slots glow gold; empty slots are dim. Right-side equip list shows slot label + item name + rarity dot; click a filled row to unequip.
- **GREEN (added) · richer `layout.equipment`:** API now returns each slot as `{name, rarity, id}` (not just a string) so the body map can colour rarity dots without a second lookup.
- **GREEN (added) · tests:** `test_api_server.py` adds `test_manual_returns_player_topics`, `test_equipment_slots_endpoint_returns_seventeen`, `test_layout_equipment_block_uses_seventeen_slots`. `test_inventory.py` adds `test_resolve_equip_slot_aliases`, `test_equip_slots_taxonomy_has_seventeen_layered_slots`, `test_legacy_equipment_dict_migrates_in_place`. **Suite: 318 passing** (was 312).
- **YELLOW (changed):** **`tests/test_inventory.py`** — `test_equip_torso_migrates_to_chest_armor` (was `test_equip_torso`) confirms the legacy `torso` slot key is stripped and the item now lives at `chest_armor`. **`core/equip_suggest.py`** rewritten to compare via `resolve_equip_slot` so upgrade hints respect the new bucket model (rings hint over rings, curios over curios, otherwise exact slot match). **`core/inventory.format_inventory_sheet`** legacy text view now lists every filled slot using two-letter slot codes (MH/OH/CHA/CHC/HD/FC/NK/BK/HN/WS/LGA/LGC/FT/R1/R2/A1/A2).
- **EFFECT:** Combat panel is no longer a red terminal block — it's a structured HUD with HP bars and clickable buttons; opening INV gives you four real action buttons per item; the equipment screen is a proper Curios-style body diagram with chest and legs split into armor + clothing layers; HANDBOOK button reads as a real player manual now.

## Multi-genre portraits landed (May 2026)

- **GREEN (added):** **`assets/ui/portraits/marshall_jr.png`**, **`dare_westsea.png`**, **`lt_keppo.png`**, **`sean_brooke.png`** — painted 90s CRPG box-art portraits matching the existing five (Garros / Aria / Thal / Kharvok / Aegis-7). Generated via Abacus Studio (Nano Banana 2) using the prompts in this chat.
- **YELLOW (changed):** **`content/presets/characters.json`** — the four multi-genre heroes now point at `.png` (the original five stay `.jpg`).
- **YELLOW (changed):** **`tests/test_preset_portraits.py`** — all nine ids are now in the `PORTRAIT_CONFIRMED` set; pending list is empty. **Suite still 312 passing.**
- **EFFECT:** Character-select grid no longer shows letter-glyph fallbacks; every hero card has real art on first load.

## One-click launcher — `Canon Engine.bat` (May 2026)

- **GREEN (added):** **`Canon Engine.bat`** at the repo root. Double-click to play: the launcher (1) stops any prior instance still holding port **8765**, (2) starts `python -m api.server` in the foreground (the console *is* the engine log), (3) auto-opens your default browser at **<http://127.0.0.1:8765/>** after a 2s delay. Close the window (or Ctrl+C) to stop. No separate "API server" step to remember.
- **YELLOW (changed):** **`README.md`** — *Run (shipped UX)* now points at the launcher first; `python -m api.server` stays as the manual equivalent.
- **CONTEXT:** Operator: *"no api server, i just want to be able to latch the api by inputting it in the setttings"*. Right call — the engine and the web UI are one process; the only thing the player should ever touch is **double-click → SETTINGS → paste key → SAVE**.

## Web HUD v1 — multi-genre, /think, INV + STATS overlays, API key UI (May 2026)

> Big batch in response to operator feedback: "not just dark fantasy", four new heroes, an interactive tutorial overlay, click-buttons for SAY/DO/THINK, INV with a body map, STATS with skill tree, and an API key field in Settings (so secrets don't have to be hand-edited in `.env`).

- **GREEN (added) · multi-genre presets:** `content/presets/characters.json` now ships **9 heroes** (was 5). New ones — **Marshall Junior** (1940s noir detective, African-American), **Dare WestSea** (sole young pirate), **Lt. Keppo** (space ranger bounty hunter from Titan; cowboy-in-space drawl), **Sean "SB" Brooke** (2000s skater with a leveling-system grafted on after a near-death — superhumans + underworld monsters world). Speech styles: **noir / pirate / western / genz** respectively. Stats balanced per archetype; portrait JPGs queued (UI falls back to a letter-glyph until you drop them at `assets/ui/portraits/<id>.jpg`). Visual descriptions written for each so AI portrait gen has a real brief.
- **GREEN (added) · `/think` command:** `core/command_parser.py` parses `/think <words>`; `ui/game_session.py` routes it through `narrate_and_apply` like `/say` and `/do`; `core/narrator.py` adds a `_THINK_INSTRUCTION` so the model treats it as **internal monologue** — NPCs don't hear it, world clock barely moves, no inventory mutations. `core/action_suggestions.py` whitelists `think` so the narrator can offer THINK chips. Tested.
- **GREEN (added) · interactive tutorial card:** `web/modules/tutorial.js` reads new `layout.tutorial` block (api/server.py snapshots `state['tutorial']` + the active step text and completion criteria). Shows step id, title, bullet text, and a plain-English "Goal" line so the player always sees what unlocks the next step. Hides itself outside tutorial mode.
- **GREEN (added) · action bar redesign:** `web/modules/action_bar.js` adds three big buttons — **SAY · DO · THINK** — above the input. Click one, type the words, hit Enter. Power users can still type raw `/commands` directly (those bypass the mode prefix). THINK button is tinted blue to match the inner-voice log style.
- **GREEN (added) · INV overlay:** `web/modules/inventory_overlay.js` — modal with two tabs: **ITEMS** (sorted by rarity, weight readout) and **EQUIPMENT** (a body-map SVG with four slots — WEAPON, TORSO, ACC. 1, ACC. 2 — that light gold when filled, plus a slot-by-slot list).
- **GREEN (added) · STATS overlay:** `web/modules/stats_overlay.js` — modal with three tabs: **STATS** (level/XP/points line, optional `LEVEL UP` button when XP is full, per-stat bars with `+` buttons that fire `/addstat <KEY>`), **SKILLS** (full tree from `layout.skills` — tier pill, label, id, and an UNLOCK button when prereq is met and a point is free; locked / unlocked states are explicit), **LORE** (live `/handbook` cards plus a recent-events strip). All buttons round-trip through `/action` so the engine stays the source of truth.
- **GREEN (added) · `layout.skills` + `layout.tutorial`:** `api/server.py` extends `layout_payload` with these two snapshot blocks so the new overlays don't need extra round trips.
- **GREEN (added) · `GET /me`:** Returns the local OS username (via `getpass.getuser`) — used as the save label in the menu footer + Settings panel. **No login screen, no email/password.** Localhost desktop app: whoever owns the desktop session owns the playthrough. Replaces the Abacus/Claude scaffold's NextAuth flow that was never welcome here.
- **GREEN (added) · `GET/POST /settings/keys`:** Reads/writes API keys to `.env` from the Settings panel. Mask-only on read (4+4 with an ellipsis — the real key never round-trips back to the browser). Write rejects newlines/quotes; supports `openrouter` / `openai` / `anthropic` and an optional `narrator_model`. Atomic write to `.env.tmp` + `os.replace`. Refreshes `os.environ` so the running engine picks up the new key without a restart.
- **GREEN (added) · Settings panel · API keys:** Provider dropdown, masked "current key" line, password-style input for the new value, narrator-model field, single SAVE button. `web/modules/settings_screen.js`.
- **GREEN (added) · ES module split:** `web/app.js` is now a tiny entry point; logic is split across `web/modules/` (`api`, `prefs`, `store`, `dom`, `toast`, `modal`, `sidebar`, `log`, `session`, `action_bar`, `tutorial`, `inventory_overlay`, `stats_overlay`, `character_select`, `settings_screen`, `modals_misc`). No file over the 300-line cap. Browser loads them natively as `<script type="module">` — still no build step.
- **GREEN (added) · tests:** `test_api_server.py` adds `test_layout_includes_skills_and_tutorial_blocks`, `test_get_me_returns_username`, `test_settings_keys_masks_and_round_trips` (snapshots/restores `.env`), `test_think_command_routes_through_narrator`. `test_command_parser.py` adds `test_think_command`. `test_preset_portraits.py` updated for the 5+4 split (confirmed-art vs portrait-pending). **Suite: 312 passing** (was 307).
- **YELLOW (changed) · main menu copy:** Subtitle now reads **"GENRE-FLUID INFINITE RPG"** with a flavor line listing the actual span — medieval steel · pirate seas · noir alleys · space ranger stations · modern street with a HUD only you can see. The "dark fantasy" framing is gone.
- **YELLOW (changed) · sidebar HUD:** Portrait fallback is now an absolute-positioned overlay so the JPG and the letter glyph are always in the same frame; modal head got a centered tab strip used by INV + STATS; suggestion chips render on a dedicated row above the action bar.
- **CONTEXT:** Operator asked: *"why we making a email and password, adjust to local pc username + pass"* and *"where in the settings can i input the api key"*. Answers shipped: **no email/password — never was implemented; OS username displays as save label**, and **API key now lives in Settings → API KEYS**, persisted to `.env`. The original Abacus/Claude scaffold's auth flow stays rejected.

## Localhost web client v0 — `web/` shell wired to FastAPI engine (May 2026)

- **GREEN (added):** **`web/index.html`**, **`web/styles.css`**, **`web/app.js`** — vanilla HTML/CSS/JS shell (no Node, no build step). Screens: **MAIN MENU** / **CHARACTER SELECT** (5 presets w/ portraits) / **SETTINGS** / **GAME HUD**. CRPG palette (dark amber + gold), CRT scanlines + flicker overlay + vignette (all toggleable in Settings). Stats sidebar with portrait, **HP/MP/STM/XP** bars, **STR/DEX/INT/CHA/CON/LCK** grid, inventory with rarity dots, companions, alert subtitle. Suggested-action chip row under the narrative log; combat banner overlay; **Journal** + **Handbook** modals fed by **`/journal`** + **`/handbook`**.
- **GREEN (added):** **`api/server.py`** — **`StaticFiles`** mounts: **`/web/*`** serves the new client and **`/assets/*`** serves portraits / audio / UI pack so JSON `res://assets/...` paths just work (rewritten to **`/assets/...`** for the browser). New endpoint **`GET /presets`** returns the five canonical heroes (Garros / Aria / Thal / Kharvok / Aegis-7) with **`portrait_url`** added. Root **`GET /`** now **307**s to **`/web/`** so `python -m api.server` + open browser is the whole flow.
- **GREEN (added):** **`tests/test_api_server.py`** — `test_presets_returns_five_canonical_heroes`, `test_root_redirects_to_web_client`, `test_web_index_html_served`. Suite at **307 passing** (was 304).
- **YELLOW (changed):** **`README.md`** — “Run (shipped UX)” is now: `python -m api.server` → open **<http://127.0.0.1:8765/>**. No second process, no Node.
- **CONTEXT:** A separately-uploaded Next.js + Prisma + NextAuth scaffold (`canon_engine_web.zip`) was treated as a **visual reference only** — its server stack was rejected because it would replace the Python engine, lose all 300+ existing tests, and pull in DB/auth/build dependencies the project explicitly forbids. We kept the look (CRT, amber CRPG palette, RPG sidebar) and threw out the stack.

## Pivot — localhost web UI; Godot client artifacts removed (May 2026)

- **RED (removed):** **`godot_pivot_spec.md`**, **`godot_ui_spec.md`**, **`Godot_v4.6.1-stable_win64.exe - Shortcut.lnk`** — direction is **browser + FastAPI on localhost**, not a Godot project in-repo (there was no `godot/` folder here; specs + shortcut were the Godot-specific leftovers).
- **YELLOW (changed):** **`.cursorrules`**, **`canon_engine.md`**, **`README.md`**, **`ui_guardrails.md`**, **`roadmap.md`**, **`CANON_ENGINE_MASTER_MANUAL.md`**, **`narrative_saga_framework.md`**, **`ui_system.md`**, **`assets/README.md`** — docs now point at **`canon_engine.md`** § HTTP bridge + **`api/server.py`** instead of deleted Godot specs.
- **YELLOW (changed):** **`tests/test_preset_portraits.py`** — presets + portraits validated under **`content/presets`** + **`assets/`** only (no duplicate **`godot/presets`** mirror).
- **YELLOW (changed):** Misc Python docstrings (**`api/server.py`**, **`core/`**, smoke tests) — say **web / HTTP client** instead of Godot where it was commentary only.

## Tutorial + handbook: story chips (May 2026)

- **GREEN (added):** **`core/tutorial.py`** — **`hydrate_tutorial_suggestion_chips_for_layout`**: while the sandbox is on step **`suggestions`**, **`layout.suggested_actions`** is **pinned** to three boxed choices (`/look`, `/scout`, `/stealth`) on every HUD refresh — so chips show immediately, not only after another narrator reply.
- **YELLOW (changed):** **`core/tutorial.py`** **`advance_tutorial`** — stepping into **`suggestions`** **clears `pending_encounter`** so a stray narrator **`state_updates`** flag cannot blank chips or trap `/look` before the scripted combat step spawns the dummy.
- **YELLOW (changed):** **`core/action_suggestions.py`** — **`layout_suggested_actions`** runs hydrate **first**, then hides chips for **combat** or **minigame**; **pending encounter** hides chips **except** on tutorial step **`suggestions`** (**`tutorial_story_suggestions_pin_active`**).
- **YELLOW (changed):** **`content/tutorial/tutorial_steps.json`** — new **suggestions** step (Godot buttons + `/look` \| `/scout` \| `/stealth` completion); wrap text points at **hud_story_suggestions**, **canonchanges** **updates_***, **saga** summary.
- **YELLOW (changed):** **`core/tutorial.py`** — **`complete_when.type` = `command_in_set`**; **`hud_event_subtitle`** copy mentions suggestion row.
- **YELLOW (changed):** **`content/handbook/topics.json`** — new **`hud_story_suggestions`**; **getting_started** / **commands_core** / **hud_journal_bridge** updated for chips, **layout.saga**, and changelog-linked **`/help`**.

---

## Suggested action chips (3 + custom line) (May 2026)

- **YELLOW (changed):** **`godot/`** — **`[ STORY PICKS ]`** section + thin panel frame between **ORDERS** and **COMMAND DECK** so boxed choices read as a deliberate slot (not a mystery overlay). **`main_layout_sync`** hint text calls that out; **`Awaiting action…`** no longer uses inner BBCode (fade stack was folding `[` into `(`).
- **GREEN (added):** **`core/action_suggestions.py`** — Validates **`suggested_actions`** from narrator JSON (medium whitelist: `/say`, `/do`, `/look`, `/scout`, `/stealth`, `/travel`), pads with fallbacks, clears each new player line; layout omits chips during **combat**, **pending encounter** (tutorial **`suggestions`** exception), or **active minigame**.
- **YELLOW (changed):** **`core/narrator.py`** — JSON contract + **`suggested_actions`** passes through **`_validate_result`** (offline/error paths included).
- **YELLOW (changed):** **`core/narrator_apply.py`** — Stashes validated chips on **`presentation.suggested_actions`** after each narration apply.
- **YELLOW (changed):** **`ui/game_session.py`** — Clears suggestions at the start of **`step_session_turn`** so only the latest beat’s chips show.
- **YELLOW (changed):** **`api/server.py`** — **`layout.suggested_actions`** for Godot binding.
- **GREEN (added):** **`godot/cinematic_hud_layout.gd`** + **`cinematic_hud_widgets.gd`** — Suggestion row under shortcut chips; **`main_layout_sync.gd`** syncs labels/tooltips/meta commands; **`game_hud.gd`** posts the same string as typing **Enter**.
- **YELLOW (changed):** **`godot_pivot_spec.md`** — Example layout includes **`suggested_actions`**.
- **GREEN (added):** **`tests/test_action_suggestions.py`** — Whitelist, padding, combat gate, layout key.
- **YELLOW (changed):** **`tests/test_playability_smoke.py`**, **`tests/support_intro_narrator.py`**, **`tests/test_narrator.py`** — Contract + fake narrator chips.

---

## In-game handbook = full changelog (May 2026)

- **GREEN (added):** **`core/handbook.py`** merges **`canonchanges.md`** into **`GET /handbook`** and **`/help`** — every `##` section becomes an **`updates_*`** topic (after **Engine updates how to read**); gameplay chapters from **`content/handbook/topics.json`** follow unchanged.
- **YELLOW (changed):** **`tools/api_server.spec`** bundles **`canonchanges.md`** at the PyInstaller root so frozen **`api_server.exe`** still exposes the changelog in the handbook.
- **YELLOW (changed):** **`godot/handbook_book_pages.gd`** cover copy mentions release notes before gameplay chapters.
- **YELLOW (changed):** **`tests/test_handbook.py`** covers merged ids + canonchanges-backed topic rendering; handbook index lines are **`[HANDBOOK]`**-prefixed so long TOCs stay visible in **`command_log_tail`**.

---

## Saga / grand-narrative framework (May 2026)

- **GREEN (added):** **`narrative_saga_framework.md`** — design law for spine vs pods, five-beat macro-loop, flag naming, and how saga plays with world bible and `state_updates`.
- **GREEN (added):** **`content/narrative/saga_seed.json`** — machine-readable spine phases, pods, and consequence guide (authoring surface for the narrator).
- **GREEN (added):** **`content/narrative/pod_quests.json`** — optional **flag → events line** hooks when saga-tagged `world_flags` become true (deduped per save).
- **GREEN (added):** **`core/saga.py`** — load corpus, **`ensure_saga`**, **`build_saga_prompt_block`**, whitelisted **`saga_advance` / `saga_hint`**, **`saga_layout_snapshot`**, pod hook processor.
- **YELLOW (changed):** **`canon_engine.md`** — documentation map row → saga framework doc.
- **YELLOW (changed):** **`core/character_session.py`**, **`core/state_manager.py`** — new sessions, demo blob, and legacy save merge all get a **`saga`** bucket with safe defaults.
- **YELLOW (changed):** **`core/narrator.py`** — **SAGA_FRAMEWORK** block after world bible; JSON instructions mention saga flag prefixes and **`saga_advance`**.
- **YELLOW (changed):** **`core/narrator_apply.py`** — applies **`saga_advance`** / **`saga_hint`** and runs pod quest hooks after each narrator result.
- **YELLOW (changed):** **`api/server.py`** — **`layout.saga`** snapshot for a future HUD “Arc” line.
- **YELLOW (changed):** **`tools/api_server.spec`** — comment that bundled **`content/`** already includes **`content/narrative/`** for frozen exe.
- **YELLOW (changed):** **`tests/test_playability_smoke.py`** — layout contract now expects **`saga`**.
- **GREEN (added):** **`tests/test_saga_framework.py`** — corpus, prompt block, legacy merge, apply path, layout, hooks.

## Preset hero portraits + Thal (May 2026)

- **GREEN (added):** **`godot/assets/ui/portraits/`** (`garros.jpg`, `aria.jpg`, `thal.jpg` — files are **JPEG**; `.png` extension caused Godot import errors) — CRPG portraits; mirrored under **`assets/ui/portraits/`** for repo parity.
- **YELLOW (changed):** **`content/presets/characters.json`** + **`godot/presets/characters.json`** — each preset has **`portrait_path`** + **`visual_description`** (art brief only, not backstory); new preset **Thal** (scholarly mage, victorian speech, INT-forward stats).
- **YELLOW (changed):** **`godot/character_select.gd`** — **`TextureRect`** shows the active preset portrait from JSON.
- **YELLOW (changed):** **`core/character_session.py`** — optional **`portrait_path`** on **`player`**; **`api/server.py`** layout exposes **`player.portrait_path`** for HUD binding.
- **GREEN (added):** **`tests/test_preset_portraits.py`** — files on disk, JSON sync, session carry **`portrait_path`**.

## Presets Kharvok + Aegis-7 (May 2026)

- **GREEN (added):** **`kharvok.jpg`**, **`aegis7.jpg`** in **`godot/assets/ui/portraits/`** (mirrored **`assets/ui/portraits/`**) — JPEG with **`.jpg`** extension; first attachment = **Aegis-7** (robot), second = **Kharvok**.
- **YELLOW (changed):** **`content/presets/characters.json`** + **`godot/presets/characters.json`** — presets **`kharvok`** (fighter, noir) and **`aegis7`** (construct, robotic); display name **Aegis-7** to match chest stencil art.
- **YELLOW (changed):** **`tests/test_preset_portraits.py`**, **`assets/README.md`** — **`aegis7`** preset id + **`aegis7.jpg`** portrait file (renamed from **Aegis-9** / **`aegis9`** for stencil alignment).

## Playability smoke gate (May 2026)

- **GREEN (added):** **`tests/test_playability_smoke.py`** — single integration test: **`GET /health`**, **`/handbook`**, **`/journal`**, **`POST /action`** with **`preset: tutorial`** then **`/look`**, plus asserts on **HUD layout** keys Godot binds (`combat_*`, `minigame_*`, `shop_*`, logs, player).
- **YELLOW (changed):** **`README.md`** — documents the gate command and clarifies what is promised (**API contract**) vs still operator-dependent (**Godot version**, **`.env`**, how you start the backend).

## Roadmap: Minigames, Journal, Auto-Boot (May 2026)

### Track M — Minigames (hybrid Godot + Python clamp)

- **GREEN (added):** **`core/minigames.py`** — Lockpick + gamble **pure logic**, **`pending_minigame`** blob, **`minigame_api_snapshot`** for layout JSON; server clamps lockpick claims; gamble uses a stored **seed**.
- **YELLOW (changed):** **`systems/minigames.py`** — Re-exports **`core.minigames`** (stub removed).
- **YELLOW (changed):** **`core/command_parser.py`**, **`ui/game_session.py`** — **`/lockpick`**, **`/gamble`**, **`/minigame_resolve`**, **`/minigame_abort`** dispatch + idle-clock skips where needed.
- **YELLOW (changed):** **`api/server.py`** — Layout merges **`minigame_api_snapshot`** after combat.
- **GREEN (added):** **`godot/hud_minigame_overlay.gd`** — Sweeps lockpick UI + gamble chips; posts resolve commands.
- **YELLOW (changed):** **`godot/game_hud.gd`**, **`godot/main_layout_sync.gd`** — Mount + sync minigame overlay.
- **GREEN (added):** **`tests/test_minigames.py`** — Window vs DEX, out-of-window reject, gamble determinism.

### Track J — Journal / Chronicle

- **GREEN (added):** **`core/journal.py`** — **`build_journal_payload`**: warm file tail + rolling **`memory.summary`** + quests + **`world_log`** chronicle (chapter markers).
- **YELLOW (changed):** **`api/server.py`** — **`GET /journal?slot=`** (optional) returns **`{ ok, journal }`**.
- **GREEN (added):** **`godot/journal_book.gd`**, **`godot/journal_book_pages.gd`**, **`godot/journal_book_shell.gd`**, **`godot/scenes/Journal.tscn`** — Flip-book UI over **`/journal`**; pause menu **Journal** returns via **`journal_return_scene`** meta (same pattern as Shop).
- **GREEN (added):** **`tests/test_journal.py`**, **`tests/test_api_server.py`** — Journal shape + bad slot **422** + API smoke.

### Track P — PyInstaller + Godot supervisor

- **GREEN (added):** **`requirements-dev.txt`** — **`pyinstaller`** only (runtime **`requirements.txt`** untouched).
- **GREEN (added):** **`tools/api_server.spec`**, **`tools/build_api_exe.py`** — One-file **`api_server.exe`** into **`godot/api_server/`**.
- **GREEN (added):** **`godot/api_supervisor.gd`** autoload (**`project.godot`** **`[autoload]`** **`ApiSupervisor`**) — **`/health`** probe, optional **`OS.create_process`**, **`tree_exiting`** **`OS.kill`**.
- **YELLOW (changed):** **`godot/settings_store.gd`** — **`auto_spawn_backend`**, **`backend_exe_path`** defaults + persist.
- **YELLOW (changed):** **`godot/ui_connection_banner.gd`**, **`godot/main_menu.gd`**, **`godot/main_menu_footer_mirror.gd`**, **`godot/game_hud.gd`** — **`STARTING ENGINE`** link state + soft re-poll while the supervisor warms the exe.

### Docs

- **YELLOW (changed):** **`README.md`**, **`godot/README.md`** — **Release bundle** / auto-boot notes; **`canonchanges.md`** (this block).

## Documentation — single index + trimmed duplicates (May 2026)

- **GREEN (added):** **`canon_engine.md` → Documentation map** — One routing table for which file owns bridge, guardrails, Godot art, changelog, Cursor rules.
- **YELLOW (changed):** **`README.md`**, **`godot/README.md`**, **`godot_pivot_spec.md`**, **`ui_system.md`**, **`godot_ui_spec.md`**, **`resolution_layout_fix_spec.md`**, **`ui_guardrails.md`**, **`CANON_ENGINE_MASTER_MANUAL.md`** §2.1/5.1 — Point at the map instead of re‑stating setup or policy **`.env`** rules in multiple places ; tests now **`pytest`** not **`unittest`** in README.
- **RED (removed):** **`cursorrulescanonengine.md`** full duplicate body — replaced with pointer to repo **`.cursorrules`** only.

## Godot HUD — narrative uses main canvas width + scroll (May 2026)

- **YELLOW (changed):** **`godot/cinematic_hud_layout.gd`** — **BottomDeck** anchors start around **22%** from the top (was **60%**) so the big middle band feeds the story, not blank space; **ScrollContainer + RichTextLabel** so long logs scroll; wrap width tracks viewport size.
- **YELLOW (changed):** **`godot/cinematic_hud_overlays.gd`** — **Landmark** block is wider; **event subtitle** column bumped right so headings and exits breathe on ultrawide; **HudHint** moved into the deck (between story and shortcut row).
- **YELLOW (changed):** **`godot/cinematic_hud_regions.gd`** — Narrative **resize / scroll** lambdas use **`instance_from_id`** so Godot does not call into **freed Node captures** (**lambda capture was freed** runtime).
- **YELLOW (changed):** **`godot/main_layout_sync.gd`** — Dropped an unused **`nm`** local in **`_sync_pillar`** (reload warning).
- **GREEN (added):** **`godot/cinematic_hud_widgets.gd`** — **`hud_section_cap_label`** + **`attach_power_pillar_vitals_cap` / `fill_cinematic_bottom_deck`** — muted **`[ SECTION ]`** labels (**Vitals**, **Site**, **Alert**, **Party**, **Chronicle**, **Orders**, **Command deck**).

## Pytest + import hygiene (May 2026)

- **YELLOW (changed):** **`tests/test_state_manager.py`** — **`build_character_session_state`** now seeds **`world_flags`** with default setting keys; tone assertion matches medieval-fantasy catalog text.
- **YELLOW (changed):** **`core/terrain.py`** — **`ensure_location`** is pulled in **lazily** inside **`_ensure_location`** so cold imports (e.g. isolated tests) avoid a **`terrain` ↔ `economy`** cycle.

## Roadmap batch — settings, backstory, companions, shop, combat HUD (May 2026)

- **GREEN (added):** **`content/settings_catalog.json`**, **`core/setting_picker.py`**, **`core/bible_seed.py`** — Pick a **primary** (and optional **collision**) setting for new heroes; **collision factor** drives how many merged **world bible** rules you get; **never wipes** operator bible keys.
- **YELLOW (changed):** **`core/character_session.py`** — Applies setting merge + bible seed on **`/start_character`**.
- **YELLOW (changed):** **`godot/create_hero_modal.gd`**, **`godot/character_select.gd`** — Setting dropdowns + **`POST /backstory`** roll (second **`HTTPRequest`**); presets can carry **`setting_*`** fields.
- **GREEN (added):** **`core/backstory.py`**, **`POST /backstory`** in **`api/server.py`** — Short JSON backstory for the create-hero form.
- **GREEN (added):** **`core/companions.py`** — **`/recruit`**, **`/dismiss`**, **`/companion`**; loyalty nudge when NPC relationships move (**`core/npc.py`** calls into companions).
- **YELLOW (changed):** **`systems/companions.py`** — Thin re-export to **`core.companions`** (old stub gone).
- **GREEN (added):** **`content/item_lore.json`**, **`core/item_lore.py`**, **`layout_inventory_rows`** in **`core/inventory.py`** — Optional **rarity card** text on inspect + Godot inventory detail.
- **YELLOW (changed):** **`api/server.py` layout** — **`shop_lines`** / **`shop_present`** for merchant UI; inventory JSON rows may include **`lore_card`** / **`rarity_blurb`**.
- **GREEN (added):** **`godot/hud_combat_overlay.gd`** — Turn/round + enemy/party lists + combat chips (**ATK/BLK/FLEE**); Flee respects confirm via dialog path.
- **YELLOW (changed):** **`godot/hud_combat_overlay.gd`** — Combat actions use **`cinematic_hud_widgets.chip_button`** (flat) instead of main-menu nine-patch chips (**`384×` min width** distorted inside the overlay). Round / enemy **`#`** index shown as ints.
- **YELLOW (changed):** **`godot/game_hud.gd`**, **`godot/main_layout_sync.gd`** — Mounts combat overlay; **Shop** entry in pause when a merchant snapshot exists; **`flee_confirmed`** one-shot on confirm.
- **YELLOW (changed):** **`ui/game_session.py`** — Combat **flee confirm** soft gate + admin/retcon/recruit handlers; extra shell kinds skip the idle clock where appropriate.
- **GREEN (added):** **`core/admin.py`**, **`/admin`**, **`/retcon`** in **`core/command_parser.py`** — Password from **`.env`** **`CANON_ADMIN_PASSWORD`**; retcon needs unlock.
- **YELLOW (changed):** **`core/narrator.py`** — **Speech style** JSON fragments + **immersion / admin** prompt lines.
- **GREEN (added):** Nine files in **`content/languages/`**, **`core/speech_styles.py`**.
- **GREEN (added):** **`godot/scenes/Shop.tscn`**, **`godot/shop_screen.gd`** — Simple merchant sheet over **`/shop`** / **`/buy`**.
- **GREEN (added):** Tests under **`tests/`** for settings, backstory, companions, admin, flee confirm, speech styles, item lore, API layout/backstory.

## Settings screen — sections + HUD/API prefs (May 2026)

- **YELLOW (changed):** **`ui_settings_screen.gd`** — Full-height **scroll** body, pinned **footer** (**HSeparator** + **Save & Back / Back (discard)**), **amber dot** + **Unsaved changes** when anything edits, terse **two-line** keybind hint.
- **GREEN (added):** **`settings_fields.gd`**, **`settings_payload.gd`**, **`settings_file_transfer.gd`**, **`settings_dialogs_mgr.gd`**, **`settings_save_validate.gd`**, **`ui_settings_widgets.gd`**, **`ui_settings_body.gd`**, **`ui_settings_mid_sections.gd`**, **`ui_settings_keybind_block.gd`** — **DISPLAY / GAMEPLAY / NARRATOR / KEYBINDINGS / SYSTEM** sections (gold headings + separators), **`user://settings.cfg`** keys for sliders/toggles/dropdowns, **IMPORT/EXPORT/CLEAR** via native dialogs (**ConfirmationDialog** danger path), **`lbl_tipped`** hover copy on essentially every row.
- **YELLOW (changed):** **`settings_store.gd`** — Saves/loads expanded client keys; **`normalize_base_url`** prepends **`http://`** when the field is host-only; **`client_prefs_for_api()`** for **`POST /action`**.
- **YELLOW (changed):** **`hud_keybinds.gd`** — Adds **F5/F6/F7** defaults for **`/attack`**, **`/flee`**, **`/map`** (stored like other HUD binds).
- **YELLOW (changed):** **`game_hud.gd`** — Attaches **`client_prefs`** blob each action; **`ui_scale`** + **`narrator_font_size`** at boot/retry; optional **`scanlines_overlay.gdshader`** layer when CRT toggle on; narrator feed respects **Show Dice Rolls**.
- **GREEN (added):** **`shaders/scanlines_overlay.gdshader`** — Light scanline darken pass.
- **YELLOW (changed):** **`main_layout_sync.gd`** — `apply_action(..., show_dice_rolls)` gates **`[check]`** append.
- **YELLOW (changed):** **`api/server.py`** — **`ActionBody`** accepts optional **`client_prefs`**; merges through **`step_session_turn`** into **`state['_client_prefs']`**.
- **YELLOW (changed):** **`ui/game_session.py`** — **`_try_autosave`** honors **autosave on/off**, **interval (1|3|5)**, **`turn % interval`**, writes **`active_slot`** path (fallback **`autosave`**).
- **YELLOW (changed):** **`core/narrator.py`** — Uses prefs for **model override**, **`max_tokens`**, **tone/difficulty** prompt lines, **rolling memory omit**, **vector block gate** (**defaults OFF**, opt-in matches Godot toggle).
- **GREEN (added):** **`tests/test_autosave_client_prefs.py`** — Interval + off-switch coverage without touching disks.

## Godot main menu polish + Manage Saves (May 2026)

- **YELLOW (changed):** **`main_menu_ui.gd`** — Menu chips gain **tiered amber** (**NEW GAME** brighter/larger hero row, **LOAD**/**MANAGE** softer), subtler hover/press pulse; disabled chips mute **glyph** tint.
- **GREEN (added):** **`main_menu_save_io.gd`**, **`main_menu_load_pick.gd`**, **`main_menu_slot_modals.gd`**, **`main_menu_overlay_notify.gd`**, **`main_menu_stack_attach.gd`**, **`main_menu_offline_modal.gd`**, **`main_menu_footer_mirror.gd`**, **`main_menu_quotes.gd`**, **`main_menu_version_corner.gd`** — Split save I/O (**delete** + **copy** with sidecars **slot_X** fallback names), LOAD picker overlay, **MANAGE SAVES** flow (**LOAD**/ **DELETE** w/ YES·CANCEL, **COPY**) + toast blurbs; centred stack + footer wiring lives in **`main_menu_stack_attach`**, API footer mirror dims green; lore quotes/version label extracted.
- **YELLOW (changed):** **`main_menu.gd`** (+ slot/load helpers) — **`preload()`** links so **`class_name`** isn’t needed at parse (clean `.godot` / editor cold start); **`Dictionary`** typed locals where inference failed; spacing/SETTINGS/footers/tooltips/`grab_focus` polish as before.

## Godot Handbook screen layout pass (May 2026)

- **YELLOW (changed):** Handbook — **`strip_noparse_tags`** + **`assign_handbook_bbcode`** remove visible **`[noparse]`** wrappers before assigning page text; page **`MarginContainer`** **30px** on all sides (panel **`StyleBoxFlat`** inner margins lowered so inset isn’t cramped); **`RichTextLabel`** **left** alignment for the **TOC**; cover **Version** tint **#777777**; **page counter** uses the same **palette** font as **HANDBOOK** with **amber** tint at **16px**.
- **YELLOW (changed):** **`handbook_book.gd`** — **Cover spread:** left page fills with **TOC** (titles from **`/handbook`**) plus **subtitle** line and **`application/config/version`**; **readable** serif stack via **`RichTextLabel`** (beige **#E8E2D6**, gold **#D4A94F**, grey instructions); **`Page X / Y`** centered between **PREV**/**NEXT**; **edge flips** at **10%** width; top bar **RESET PAGE** (!= RETRY), side buttons visually lighter.
- **GREEN (added):** **`handbook_book_pages.gd`** + **`handbook_book_chrome.gd`** — **BBCode** text builders + parchment **panel**/top-button styling so the main handbook script stays under the **300**-line guideline.

## Godot HUD — Juncture 1.1 refinement (May 2026)

- **YELLOW (changed):** **`cinematic_hud_layout.gd`** — **`BottomDeck`** (**`VBoxContainer`**, anchors **0.15 / 0.6 / 0.95 / 0.98**, separation **10**, **`MOUSE_FILTER_PASS`**) stacks **`NarrativeLog`** (expand+fill, clip, scroll-follow) → **`ShortcutRow`** (min height **40**) → **`InputBar`** **`HBoxContainer`** (min height **50**, **`LineEdit`** + **MENU**); removes overlap with manual anchor stacking.
- **YELLOW (changed):** **`cinematic_hud_layout.gd`** — Removed pillar **grey panel**; **thin centered Vita-Line** (~26px) + **horizontal XP** strip; **left-aligned** stack; narrator default **#EEEEEE**; **HELP / LOOK / INV …** via **`chip_command_button`** (slightly smaller chips).
- **YELLOW (changed):** **`cinematic_hud_widgets.gd`** — **`chip_command_button`**, **`horizontal_meter`**, **`style_health_fill`** (muted greens, **≤30% HP** toward red, poison/bleed); softer Vita **glow**.
- **YELLOW (changed):** **`cinematic_hud_overlays.gd`** — **Landmark** three-line stack: **location** (teal), **exits** (dim), **`landmark_player`** (**Name · Lv**); hint band nudged above narration.
- **YELLOW (changed):** **`main_layout_sync.gd`** — Pillar label **Lv only** (name on landmark); **idle** line **`[ Awaiting action... ]`**; **BBCode** stack fresher **#eaeaea**; **HP fill** restyled each sync.
- **YELLOW (changed):** **`game_hud.gd`** — **Placeholder** lines rotate after each **`POST /action`** success.

## Godot HUD — anchor-only cinematic tree (May 2026)

- **YELLOW (changed):** **`cinematic_hud_layout.gd`** — Rebuilt without **VBox/HBox** skeleton: **fractional anchor zones** via **`cinematic_hud_regions.gd`**, pillar **0.15** width, horizon **top 0.7–bottom 1** with **zero** root offsets; **draw order** narrative → chips → **InputDeck** (50px) so the line never sits under the log; **Vita-Line** fill uses optional **glow** on the stylebox.
- **YELLOW (changed):** **`cinematic_hud_overlays.gd`** — Location / exits / hint / event block use **anchor-only** rects; location title **#008080** teal; event strip **right-aligned** **0.5–0.95**; companion rail is a plain **`Control`** (pips positioned in **`main_layout_sync.gd`**).
- **GREEN (added):** **`scenes/hud.tscn`** — Same **`game_hud.gd`** entry as **`GameHUD.tscn`** (optional scene path); root node name **`HUD`**.
- **YELLOW (changed):** **`game_hud_layout.gd`** (legacy grid) — Panel **flavor** subtitles cleared (no **Mk.III** / **v0.7** strings).

## Godot HUD — Juncture 1 tighten pass (May 2026)

- **GREEN (added):** **`godot/vit_line_pulse.gd`** — Vita-Line **slow luminance pulse**; **`set_vita_status_tint`** keeps **poison/bleed/low-HP** coloring without the old integer-division warning.
- **YELLOW (changed):** **`godot/main_layout_sync.gd`** — Low-HP check uses **≤ 20% HP** via floats; pillar talks to **`set_vita_status_tint`** when present. **Event subtitle** prefers **`layout.hud_event_subtitle`**, then **`events[0]`**.
- **YELLOW (changed):** **`godot/hud_inventory_overlay.gd`** — **Right-edge drawer** (slide tween + dim **click-to-close**); less “full-screen modal,” more **Mission Control** overlap.
- **GREEN (added):** **`layout.hud_event_subtitle`** — **`api/server.py`** **`layout_payload`**; cleared at each **`step_session_turn`** in **`ui/game_session.py`** so a turn can set a fresh toast. **Tutorial** uses it instead of **`events[0]`**.
- **YELLOW (changed):** **`godot/cinematic_hud_widgets.gd`** + layout/overlays — **`SystemFont`** serif stack for **landmark title** + **narrative horizon** (Georgia / Times / DejaVu / Liberation / Noto fallbacks).
- **YELLOW (changed):** **`godot/game_hud.gd`** — On **Enter**, a **cyan command tracer** tweens from the deck toward the horizon, then fades.

## Godot HUD — command log layout (May 2026)

- **YELLOW (changed):** **`godot/game_hud_layout.gd`** — Command log panel was sometimes **shorter than its real minimum** (frame header + ninepatch + margins + metallic **`TextEdit`** theme), so the log **drew on top of** the `/command` row. Now the log wrapper has a **fixed minimum height**, the **middle band** is **10px shorter** so everything still fits a **720**-tall layout, and the **command column clips** so nothing bleeds over the invoke bar.
- **GREEN (added):** **`godot/game_hud_resize.gd`**, **`godot/game_hud_layout_rtl.gd`** — **`apply_window_mins`** (no more forcing **1280×720** every frame) and **`apply_hsplit`** keep the **world vs. rail** split near **~59%** width as you resize; **`game_hud_layout.gd`** gives the **middle strip** most of the **extra height** (**stretch ratio** vs. command stack) so **16:9** and **tall / portrait** windows grow the **WORLD VIEW** instead of only the log.
- **YELLOW (changed):** **`godot/game_hud.gd`**, **`godot/main.gd`**, **`godot/boot.gd`** — Window **minimum** is **480×720** (layout still targets **720** tall); **GameHUD** listens for **`resized`** and updates the **`HSplitContainer`**.
- **YELLOW (changed):** **`godot/game_hud_layout.gd`** — **COMMAND LOG** no longer shares a inner **`VBox`** with the invoke row; the **`>` / LineEdit / MENU** row is its own rows under the HUD root so wide windows never **clip** or collapse the action bar.
- **YELLOW (changed):** **`godot/game_hud_layout.gd`** — **WORLD splitter** + **COMMAND LOG** live in **`mid_log_body`**; only that block competes for **vertical stretch**. **Sep + invoke row** sit on the HUD root beneath it so the **HSplit**/ninepatch slice can never **crowd out** **`LineEdit`**; **`mid_log_body.clip_contents`** cages frame overflow.
- **GREEN (added):** **`godot/game_hud_invoke_dock.gd`** — **`/`** prompt + **LineEdit** + **MENU** render on **CanvasLayer 135** (**above** PS1 post **128**) with the same side/bottom margins as the HUD so the action bar is never lost to shader/compositing; layout keeps a **bottom spacer** so the log column does not overlap that strip.
- **YELLOW (changed):** **`godot/game_hud_invoke_dock.gd`** — Invoke strip is **bottom-anchored only** (`sep` + row height), not a **full-screen** stack, so **wheel / drag** reaches the **COMMAND LOG** **`TextEdit`** again.

## v0.3.8.1 — Tutorial sandbox + handbook + main menu

- **GREEN (added):** **`content/handbook/topics.json`** and **`content/tutorial/tutorial_steps.json`** — help topics and a guided tutorial checklist (data-driven).
- **GREEN (added):** **`core/handbook.py`**, **`core/tutorial.py`** — load/render handbook; tutorial step machine, **`build_tutorial_session_state`**, encounter hook for the practice dummy.
- **GREEN (added):** Main menu entries in **`ui/start_screen.py`** — new game, load slot, tutorial sandbox, handbook browser, quit.
- **YELLOW (changed):** **`/help`** — handbook index or **`/help <topic_id>`** (log lines tagged **`[HANDBOOK]`**).
- **YELLOW (changed):** **`/look`** (no args) — **`look_around`** location/minimap blurb in the command log.
- **YELLOW (changed):** Tutorial-only **`/tutorial`**, **`/tutorial next`**, **`/tutorial reset`**, **`/tutorial exit`**; campaign sessions get a clear “sandbox only” message if misused.
- **YELLOW (changed):** **`run_mode`** + **`tutorial`** blob on session state (**`core/state_manager.py`**, **`core/character_session.py`**) — **`ensure_tutorial_state`** on merge/new characters.
- **YELLOW (changed):** **`/save`** and **`/quicksave`** blocked in tutorial; **autosave** skipped so campaign slots are not overwritten.
- **YELLOW (changed):** **`core/combat.py`** — tutorial victories skip XP, loot rolls, gold, and kill quest credit.
- **YELLOW (changed):** **`ui/game_layout.py`** — tutorial header strip above the command log when the sandbox is active.
- **GREEN (added):** **`tests/test_handbook.py`**, **`tests/test_tutorial.py`**, **`tests/test_tutorial_save_guard.py`**; parser/start-screen/API tests nudged for the new menu and **`[HANDBOOK]`** tail.
- **YELLOW (changed):** **Godot + API** — main menu **TUTORIAL** / **HANDBOOK** chips; **`POST /action`** accepts optional **`preset`: `"tutorial"` \| `"demo"`** to swap the server session before the command (Godot HUD bootstraps tutorial/handbook without duplicating Python UI).
- **GREEN (added):** **`GET /handbook`** — JSON topics for Godot; **`scenes/HandbookBook.tscn`** + **`handbook_book.gd`** — two-page spread reader (Prev/Next, arrows, edge-click flip), not the HUD log.
- **YELLOW (changed):** **Juncture 1 (Godot main menu only)** — **`main_menu.gd`** / **`main_menu_ui.gd`**: NEW GAME / CONTINUE / LOAD hierarchy, teal secondary row (Tutorial+Handbook), dim+red utility row, rotating ambient lore line, `application/config/version` top-right, last-save footer from `saves/*.json`, load picker modal, **`game_hud.gd`** reads **`auto_load_slot`** for Continue/Load → **`POST /load`**.
- **YELLOW (changed):** **`godot/main.tscn` + `main.gd`** — **F5** = main menu first, then **`GameHUD`** is **parented under the same `Main` root** when you **Continue / Tutorial / Load** (no duplicate HUD `_ready` until you start). **`main_menu.gd`** calls **`_enter_game_hud()`** so **`Boot.tscn` / standalone `MainMenu.tscn`** still **`change_scene`s** to the HUD. Lore lines stay **`const` `Array[String]`** (Godot const fix).
- **GREEN (added):** **`godot/game_hud_chrome.gd`** — top **chrome**: **`banner_anchor`** for **LINK**, turn/slot/gold, **HP/XP** bars, quick **`/help` `/look` `/i` `/quests` `/save`** (save = green), **F-key** tooltips.
- **YELLOW (changed):** **`godot/game_hud_layout.gd`** — **`POSTFX_INSET_TOP`** clips the PS1 pass below chrome so LINK stays sharp; **HSeparator** above invoke; **SYSTEM** → **AUX STATUS RAIL**.
- **YELLOW (changed):** **`godot/game_hud.gd`** — quick keys read from **`user://settings.cfg`** via **`hud_keybinds.gd`** (defaults **F1–F4**, **F9**); LINK in chrome (**CanvasLayer 210** fallback); **debug** on **layer 211**.
- **GREEN (added):** **`godot/hud_keybinds.gd`** — ids, defaults, **`read_keybinds`**, **`validate_unique_keybinds`**.
- **YELLOW (changed):** **`godot/settings_store.gd`** / **`ui_settings_screen.gd`** — **HUD quick keys** UI (capture + **Reset** + save validation); five **`keybind_*`** entries in cfg.
- **YELLOW (changed):** **`godot/main_layout_sync.gd`** — drives chrome session + bars; **STATUS** panel drops duplicate HP/XP text (bars carry that); **SYSTEM** strip shows fatigue / shelter / stat points only (no duplicate turn line).

## v0.5.2 — Dynamic quests (templates, progress, turn-in)

- **GREEN (added):** **`content/quest_templates.json`** — delivery, hunt, fetch, travel, investigation patterns with reward bases and faction/relationship hooks.
- **GREEN (added):** **`core/quests.py`** — **`generate_quest_offer`**, **`offer_quests_for_npc`**, **`seed_merchant_quest_offers`** (wired from **`apply_procedural_world`**), **`accept_quest`**, **`abandon_quest`**, **`turn_in_quest`**, **`update_quest_progress`**, **`fail_expired_quests`**, list/detail formatters, **`resolve_gift`** / **`resolve_threaten`** (NPC gift/threat flows).
- **GREEN (added):** **`core/quest_rewards.py`** — **`calculate_rewards`**, **`apply_rewards`** (gold, XP, merchant-catalog items).
- **YELLOW (changed):** **`core/combat.py`** — victory path feeds kill events into quest progress.
- **YELLOW (changed):** **`core/crafting.py`** — successful craft emits **`craft_item`** quest progress.
- **YELLOW (changed):** **`ui/game_session.py`** — travel arrival updates **`travel`** objectives; **`/quests`**, **`/quest`**, **`/accept`**, **`/abandon`**, **`/turnin`**; each turn runs **`fail_expired_quests`**.
- **YELLOW (changed):** **`core/command_parser.py`** — quest slash heads.
- **YELLOW (changed):** **`core/factions.py`** — **`abandon_quest`** reputation delta (**`-8`**).
- **YELLOW (changed):** **`core/worldgen.py`** — **`reveal_lore_fragment`** also nudges investigation objectives.
- **GREEN (added):** **`tests/test_quests_generation.py`**, **`tests/test_quests_progress.py`**, **`tests/test_quests_turnin.py`**. **224** tests green.

## v0.5.1 — NPC registry, relationships, warm memory, shop bias

- **GREEN (added):** **`content/npcs_seed_templates.json`** — name pools, roles, weights, faction fallback.
- **GREEN (added):** **`core/npc.py`** — **`ensure_npcs`**, **`get_npc`**, **`get_npcs_in_location`**, **`apply_relationship_delta`** (±100 clamp), **`record_npc_memory_event`**, **`maybe_refresh_npc_summary`**, **`shop_price_multiplier`**, **`primary_merchant_npc_id`**, **`seed_world_npcs`**, **`format_npc_sheet`**, **`format_npcs_here`**.
- **GREEN (added):** **`core/npc_memory_cold.py`** — optional Chroma collection per slot (`NPC_MEMORY_COLD_ENABLED`, default off); **`index_npc_memory_event`**, **`query_npc_cold_memory`**.
- **YELLOW (changed):** **`core/world.py`** **`ensure_world`** — defaults **`npcs`**, **`quests`** skeleton.
- **YELLOW (changed):** **`core/economy.py`** — merchant blob gets **`npc_id`** when a merchant NPC is at the location; **`_merchant_for_pricing`** layers faction tier + NPC relationship into buy/sell prices.
- **YELLOW (changed):** **`core/worldgen.py`** **`apply_procedural_world`** — resets **`npcs`**/**`quests`**, seeds NPCs, seeds merchant quest offers.
- **YELLOW (changed):** **`core/command_parser.py`** + **`ui/game_session.py`** — **`/npcs`**, **`/npc`**, **`/gift`**, **`/threaten`**.
- **GREEN (added):** **`tests/test_npc_relationships.py`**, **`tests/test_npc_memory.py`**; **`tests/conftest.py`** sets **`NPC_MEMORY_COLD_ENABLED=0`**.

## v0.5.0 — Seeded world generation, procedural map, lore deck

- **GREEN (added):** **`content/worldgen_tables.json`** — biome weights, features by biome, place-name fragments, lore templates, faction influence pool.
- **GREEN (added):** **`core/worldgen.py`** — deterministic **`generate_world`** / map graph / lore deck, **`map_to_travel_edges`**, **`apply_procedural_world`**, **`sync_current_location_from_map`**, **`reveal_lore_fragment`**, **`/world`** and **`/map`** formatters, **`graph_is_connected`** (tests).
- **YELLOW (changed):** **`core/world.py`** **`ensure_world`** — defaults for **`seed`**, **`world_id`**, **`generated`**, **`procedural_map`**, **`location_id`**, **`map`**, **`lore`**.
- **YELLOW (changed):** **`core/travel.py`** — after travel, if the edge carries **`location_id`**, updates **`world.location_id`** and syncs the procedural node into **`world.location`** + session labels.
- **YELLOW (changed):** **`core/character_session.py`** — new runs call **`apply_procedural_world`** with a boot RNG derived from **`world_seed`** or name; opening text and bible rules are place-agnostic until the hub exists.
- **YELLOW (changed):** **`core/command_parser.py`** — **`/world`**, **`/map`**; dev-only **`/setseed`**.
- **YELLOW (changed):** **`ui/game_session.py`** — handlers, help line, encounter/combat allowlists; **`/travel`** uses a seed-derived RNG instead of an unseeded **`Random()`**.
- **GREEN (added):** **`tests/test_worldgen.py`**; parser/state tests updated for procedural starts.

## v0.4.3 — Death, CON/LCK, underworld, rebirth, narrator bias

- **GREEN (added):** **`core/stats.py`** — CON/LCK table modifiers, **`calculate_max_hp`** (`50 + CON×5`), **`nap_heal_amount`** / **`sleep_heal_amount`**, optional **`luck_decays`** via **`world_bible.luck_decays`**, **`earned_greatness_threshold_met`** (level ≥10, boss flag, honored+ faction, optional rebirth gate from bible).
- **GREEN (added):** **`core/death.py`** — death save (nat 1 / nat 20 bands, CON+LCK mods), **`trigger_death`**, **`after_hp_zero`** hook, dying-unstabilized path.
- **GREEN (added):** **`core/underworld.py`** — soul blob, **`enter_underworld`**, alive visit (**`soul_lantern`**, **`veil_walk`**, gate id), **`/soul`** sheet, erosion tick when bible luck_decays + no anchors, ascend/descend honor/chaos gates.
- **GREEN (added):** **`core/rebirth.py`** — standard / ascension / descension / purgatory negotiated / permanent, **`fallen_heroes`** log, faction rep halve on standard.
- **YELLOW (changed):** **`core/status.py`** — **`dying`** / **`wounded`** registry; tick damage uses CON vs poison/bleed; dying expiry → **`death.on_dying_expired`**; player tick passes **`rng`** into death hook.
- **YELLOW (changed):** **`core/combat.py`** — defeat no longer floors HP to 1; calls **`death.after_hp_zero`**; status tick gets injected RNG.
- **YELLOW (changed):** **`core/stealth.py`** — trap damage can reach 0 HP + death save; **`core/recovery.py`** — nap/sleep HP use CON formulas (sleep no longer always to full max).
- **YELLOW (changed):** **`core/leveling.py`**, **`character_session.py`**, **`state_manager.py`**, **`core/world.py`** — CON/LCK on players, **`alive`**, rebirth block defaults, **`honor_score` / `chaos_score` / `fallen_heroes`**, demo **`defeated_named_boss`** via boss defeat.
- **YELLOW (changed):** **`core/economy.py`** — lazy **`restore_companions_full`** import (breaks import cycle with terrain); scavenge roll adds LCK table modifier.
- **YELLOW (changed):** **`core/crafting.py`** — craft skill roll + LCK modifier.
- **YELLOW (changed):** **`core/narrator.py`** — v0.4.3 **NARRATOR_BIAS_RULES** + greatness gate line in system prompt.
- **YELLOW (changed):** **`core/command_parser.py`** + **`ui/game_session.py`** — **`/soul`**, **`/remember`**, **`/anchor`**, **`/bribe`**, **`/ascend`**, **`/descend`**, **`/underworld enter`**, **`/death_continue`**, **`/death_yield`**, **`/rebirth <path>`**.
- **GREEN (added):** **`tests/test_death.py`**, **`tests/test_underworld.py`**, **`tests/test_rebirth.py`**, **`tests/test_con_lck.py`**. **197** tests green.

## v0.3.9–v0.4.2 — Crafting, skill trees, bosses, factions (master spec)

- **GREEN (added):** **`content/recipes.json`**, **`content/craft_catalog.json`**, **`core/crafting.py`** — **`/craft list`**, **`/craft <id>`** (roll vs DC, quality tiers, mats always consumed, **`apply_time_passed`** for **`time_cost`**), **`reset_crafting_caches`** for tests.
- **GREEN (added):** **`content/skills_trees.json`**, **`core/skills.py`** — four trees, **`/skills`**, **`/unlock`**, **`/use`** hooks (cleave splash, backstab, analyze, amplify, forager/pathfinder passives, smoke bomb flee, etc.), **`reset_skill_tree_cache`**.
- **YELLOW (changed):** **`core/leveling.py`** — each level-up adds **one skill point** on top of stat points.
- **GREEN (added):** **`content/bosses.json`**, **`core/boss.py`** — phase thresholds, boss abilities, death loot + boss XP, **`reset_boss_cache`**.
- **YELLOW (changed):** **`core/combat.py`** — boss combat flags, phase shift after damage, cleave / skills integration.
- **GREEN (added):** **`content/factions.json`**, **`core/factions.py`** — reputation events, tiers, shop modifier / access, nemesis encounter flag, **`reset_faction_defs_cache`**; **`ensure_factions`** always syncs **`tier`** from numeric rep.
- **YELLOW (changed):** **`core/economy.py`**, **`content/merchants.json`** — faction-tied shop prices and refusal when hostile; forager **passive** scavenge DC (**`scavenge_dc_bonus`**).
- **YELLOW (changed):** **`core/stealth.py`** — Pathfinder lowers **`/scout`** DC via **`scout_dc_modifier`** (import from **`skills`** inside **`resolve_scout`**).
- **YELLOW (changed):** **`core/command_parser.py`** — **`/skills`**, **`/unlock`**, **`/factions`**, **`/reputation`** (plus existing **`/craft`**).
- **GREEN (added):** **`tests/test_crafting.py`**, **`tests/test_skills.py`**, **`tests/test_boss.py`**, **`tests/test_factions.py`**; parser tests for new commands. **179** tests green.

## v0.3.7–v0.3.8 — Elemental damage + scout / stealth / traps

- **GREEN (added):** **`core/damage_types.py`** — canonical **`DAMAGE_TYPES`**, **`normalize_damage_type`**, **`get_element_label`** (split out so inventory does not import **`elements`** in a circle).
- **GREEN (added):** **`core/elements.py`** — resistances (player torso + **`player.resistances`**, foe **`resistances`**), **split** physical vs elemental mitigation, **weather synergy** (soaked target + rain/storm boosts lightning; frost bump in wet/fog/storm), **`set_last_element_context`** → **`presentation`** for the narrator.
- **YELLOW (changed):** **`core/combat.py`**, **`core/enemy_ai.py`**, **`core/party.py`**, **`core/terrain.py`**, failed **`/flee`** retaliation — all HP loss from weapon or typed foe packets routes through **`calculate_elemental_damage`**; **ambush** consumes **`stealth_surprise_next`** into **`suppress_enemy_phase_once`** (one skipped enemy phase).
- **YELLOW (changed):** **`content/enemies.json`** — per-type **`resistances`**, **`perception_dc`** for stealth checks.
- **GREEN (added):** **`core/stealth.py`**, **`content/traps.json`** — **`/scout`**, **`/stealth`**, **`/detect`**, **`/disarm`**, **`travel_trap_hook`** ( **`on_move`** traps after **`apply_engine_travel`** ), lit areas break stealth, trap hits break stealth.
- **YELLOW (changed):** **`core/economy.py`** **`ensure_location`** — **`scout_dc`**, **`lit_area`** defaults; **`core/travel.py`** copies optional **`lit_area`** from travel edges onto the session location.
- **YELLOW (changed):** **`core/encounter_bridge.py`** — hydrates **`perception_dc`** from the bestiary.
- **YELLOW (changed):** **`core/inventory.py`** **`normalize_item`** — optional **`damage_type`**, **`elemental_bonus`** on gear.
- **YELLOW (changed):** **`core/state_manager.py`** demo — equipped **fire-tagged** longsword, **`active_traps`**, **`scout_dc`**, surface travel edge **`lit_area`**.
- **YELLOW (changed):** **`core/command_parser.py`** + **`ui/game_session.py`** — new slash commands (allowed in standoff where noted), **`/say`** and **`/attack`** respect stealth break rules, travel runs trap hook.
- **YELLOW (changed):** **`core/narrator.py`** — system prompt includes **`LAST_HIT_ENGINE`** when presentation holds last hit metadata.
- **GREEN (added):** **`tests/test_elements.py`**, **`tests/test_stealth.py`**. **146** tests green.

## v0.3.6 — Environmental tactics & terrain

- **GREEN (added):** **`core/terrain.py`** — **`get_terrain_modifiers`**, **`world_combat_stat_adjust`** (terrain + hazard DEX), **`enemy_ac_terrain_adjust`**, **`enemy_hit_footing_bonus`** (forest beasts), **`start_combat_trim_enemies`** (narrow passage), **`terrain_hazards`** tick, **`apply_feature_interaction`**, **`resolve_cover`**, **`resolve_climb`**, **`on_player_attack_roll`** (ice nat-1 slip).
- **GREEN (added):** **`content/terrain_features.json`** — oil barrel hazard, chandelier AoE, narrow cap.
- **YELLOW (changed):** **`core/status.py`** — **`covered`** (+2 AC, clears on **attack** / **travel**), **`high_ground`** (+2 **ATK**, clears on **flee** / **combat** / **travel**).
- **YELLOW (changed):** **`core/combat.py`** — footing on **AC** / **flee** / **weapon damage STR**; **enemy AC** vs player attacks; **attack** trigger clears cover before the roll; **hazard tick** at start of **enemy** phase; **narrow** trim + **`end_combat`** clears **combat**-trigger statuses.
- **YELLOW (changed):** **`core/enemy_ai.py`** + **`core/party.py`** — footing / forest hit bonuses on foe swings.
- **YELLOW (changed):** **`core/command_parser.py`** + **`ui/game_session.py`** — **`/cover`**, **`/climb`**, **`/interact`** (combat shell).
- **YELLOW (changed):** **`core/state_manager.py`** demo location — **`cover_available`**, **`high_ground_available`**, **`oil_barrel`** feature.
- **GREEN (added):** **`tests/test_terrain.py`** (+ parser bumps). **138** tests green.

## v0.3.5 — Scavenging, economy & shops

- **GREEN (added):** **`core/economy.py`** — wallet (**`gold`**, **`gold_spent`**), **victory gold + monster parts** (typed drops), **`/scavenge`** (LCK vs location **`scavenge_dc`**, +15m via **`apply_time_passed`**), merchant **stock** generation, **`calculate_buy_price` / `calculate_sell_price`**, **`/barter`** (CHA DC 12, discount on pass, disposition hit on fail), **`/rent`** (inn gold + 8h + **`well_rested`** + **`sheltered`** + **`__sleep__`** narration).
- **GREEN (added):** **`content/merchants.json`** — catalog + **`default`** / **`blacksmith`** presets; **`content/monster_parts.json`** — post-combat **material** drops by foe type.
- **YELLOW (changed):** **`content/enemies.json`** — optional **`gold_drop`** `[lo, hi]` per type.
- **YELLOW (changed):** **`core/combat.py`** — victory path calls **`grant_victory_gold_and_parts`**.
- **YELLOW (changed):** **`core/inventory.py`** — **`GOLD_WEIGHT_PER_COIN`** (0.02) folded into **`sync_carry`** totals.
- **YELLOW (changed):** **`core/leveling.py`** + **`character_session`** + **`state_manager`** — default **`gold_spent`**, demo **`world.location`** (**`has_merchant`**, **`has_inn`**, **`scavenge_dc`**, inn cost, preset).
- **YELLOW (changed):** **`core/command_parser.py`** + **`ui/game_session.py`** — **`/scavenge`**, **`/shop`**, **`/buy`**, **`/sell`**, **`/barter`**, **`/rent`** (blocked in combat / standoff shell).
- **GREEN (added):** **`tests/test_economy.py`**. **129** tests green.

## v0.3.3–v0.3.4 — UI polish + party combat

- **GREEN (added):** **`core/party.py`** — build combat **`party[]`** from **`companions`**, **`/order`** queue (**attack / block / item / flee**), loyalty obedience rolls, **party phase** after your **attack / block / item**, **combo** damage when a companion strikes the same foe you just hit, **sync** vitals back on **`end_combat`**, **nap/sleep** companion HP hooks.
- **GREEN (added):** **`render_hp_bar`** in **`core/combat_math.py`** — plain-text **`█`/`░`** meter for the combat banner.
- **YELLOW (changed):** **`core/combat.py`** — combat blob gains **`party`**, combo flags, **`combat_api_snapshot()`** for Godot JSON, richer **`combat_layout_banner`**, **`combat_open_player_tick`** clears **`combo_triggered`** when a new player-facing tick opens.
- **YELLOW (changed):** **`api/server.py`** layout merges **`combat_active`**, **`combat_round`**, **`combat_turn`**, **`combat_player_hp`**, **`combat_enemies[]`**, **`combat_party[]`**, **`combo_triggered`**.
- **YELLOW (changed):** **`godot/main_layout_sync.gd`** — prepends **`combat_banner`** above the world log when a bout is live.
- **YELLOW (changed):** **`core/recovery.py`** — **nap** tops up companions **~15%**; **deep sleep** refills companion HP to max (unless **`in_combat_defeated`**).
- **YELLOW (changed):** **`core/state_manager.py`** demo **Crypt Skeleton** now has **`hp` / `hp_max` / stats** for combat.
- **GREEN (added):** **`tests/test_layout_combat.py`**, **`tests/test_party_combat.py`**, parser + API snapshot bumps. **117** tests green.

## v0.3.2 — Multi-enemy combat + enemy AI module

- **GREEN (added):** **`core/combat_math.py`** — shared **d20 / AC / damage** helpers for combat + AI.
- **GREEN (added):** **`core/enemy_ai.py`** — **intent** bands (self low HP / player low HP / default), **per-type abilities** (Bone Rattle / Feral Lunge / Shield Bash) with **cooldowns**, **`resolve_enemy_turn`** (tick → stun skip → resolve).
- **RED (removed):** Single **`state["combat"]["enemy"]`** blob — replaced by **`enemies[]`** + **`active_enemy_index`** (no legacy shim per spec).
- **YELLOW (changed):** **`core/combat.py`** — **`start_combat`** reads optional **`encounter_data["enemy_types"]`** (up to **3**); **XP** sums per-foe rolls; **loot** one **`roll_rarity`** line per foe; **flee** contests **highest living foe DEX**; **`/attack [index]`** targeting + default **lowest HP**; **`format_combat_enemies_look`** for **`/look enemies`**.
- **YELLOW (changed):** **`core/command_parser.py`** — **`/attack`**, **`/attack N`**, **`/look enemies`**.
- **YELLOW (changed):** **`ui/game_session.py`** — combat shell + **`look_enemies`**; **`resolve_combat_item`** RNG fallback seeded from **`turn`** (no bare **`Random()`**).
- **GREEN (added):** **`tests/test_multi_enemy.py`** (+ parser bumps). **108** tests green.

## Hygiene — combat RNG, stubs, autosave, specs, roadmap

- **YELLOW (changed):** **`core/combat.py`** — **`combat_open_player_tick(state, rng)`** threads the caller’s RNG into **`end_combat`** when status tick drops the player to 0 HP (**replays/tests stay deterministic**).
- **YELLOW (changed):** **`core/status.py`** — **`exploration_tick_allowed`** only checks **`combat.active`** (retired **`stub`** flag).
- **YELLOW (changed):** **`ui/game_session.py`** — failed autosave writes one **`[AUTOSAVE]`** line instead of failing silently.
- **YELLOW (changed):** **`canon_engine.md`** — documents **`state["combat"]`** dict (**not** **`CombatSession`**), world-clock façade (**`advance_world_time` → `apply_time_passed`**), and a **pre–v0.4.0 file-split** cue for oversized modules.
- **YELLOW (changed):** **`.cursorrules`** — single bullet on world-clock authority + façade.

## Governance + combat stun — FastAPI carve-out + mirrored enemy skip

- **YELLOW (changed):** **`.cursorrules`** + **`canon_engine.md`** — **FastAPI/Uvicorn** are documented as the **permanent, intentional Godot ↔ Python bridge** only (localhost JSON — **not** a public web product); do not rip out without replacing the transport contract.
- **YELLOW (changed):** **`core/status.py`** — **`stunned`** default duration **bumped to 2** so **after** `combat_tick_*` (duration step) **`has_skip_turn_*` still fires** for exactly one forfeited combat slot (*tick-first*, then skip — same semantics player and foe).
- **GREEN (added):** **`has_skip_turn_for_statuses`** + **`has_skip_turn_enemy`**; **`enemy_turn_resolve`** skips AI offense after the enemy opening tick while stun persists.
- **GREEN (added):** Regression tests for enemy stun cadence plus player stun paired with **`combat_tick_player_start`**.

## v0.3.0 Part 1 — Encounter bridge (pre-combat standoff)

- **GREEN (added):** **`content/enemies.json`** — starter bestiary keys **`skeleton`** / **`guard`** / **`beast`** so engine can resolve DEX contests and HP while the AI only narrates.
- **GREEN (added):** **`core/encounter_bridge.py`** — **`pending_encounter`** + **`encounter_data`** helpers, CHA talk bands (peace / intimidate / fail), DEX flee contest, intimidation HP chip, **`transition_to_combat_stub`** (sets **`state["combat"]`** with **`stub: true`** so Part 2 can replace it without locking every slash command early).
- **GREEN (added):** **`core/encounter_session.py`** — wires **`/talk`**, **`/flee`**, **`/fight`** to engine rolls → narrator specials (`__encounter_*__` payloads) → apply.
- **YELLOW (changed):** **`core/world.ensure_world`** — defaults **`pending_encounter`**, **`encounter_data`**.
- **YELLOW (changed):** **`core/narrator_apply.py`** — **`state_updates`**: merges **`encounter_data`**, honors **`pending_encounter`**, applies **`force_combat`** → combat stub + clears standoff.
- **YELLOW (changed):** **`core/narrator.py`** — JSON instructions + offline fallbacks + system branches for bridge beats; narrator may still **set** a standoff via **`pending_encounter` / `encounter_data`** from normal `/say` / `/do`.
- **YELLOW (changed):** **`core/command_parser.py`** + **`ui/game_session.py`** — while **`pending_encounter`**, normal commands route to **[ENCOUNTER] … /talk | /flee | /fight** (plus **`/help`**, quit/menu); **`/fight`** clears standoff into stub combat block.
- **GREEN (added):** Tests **`tests/test_encounter_bridge.py`** (+ parser assertions).

## v0.3.0 Parts 2–4 + v0.3.1 — Live combat slice + ailments in melee

- **GREEN (added):** **`core/combat.py`** — real **`start_combat` / `end_combat`**, **`/attack`** & **`/block`** resolution, athletics **`/flee`** during a bout (failed flee earns one retaliation, not double turns), **`/item`** pouch uses consumables (**`effects`**: **`heal_hp`**, **`remove_status`**, **`apply_status`**), foe AI patterns (**beast / skeleton / guard**), **`[STATUS]`** DoT ticks at player turn open, **`stunned`** skips your action roll.
- **YELLOW (changed):** **Standoff parsers** → **`kind: flee`**, **`fight`** (no more **`encounter_flee`** / **`encounter_fight`** kinds); **`/attack`**, **`/block`**, **`/item`** for live combat only.
- **YELLOW (changed):** **`ui/game_session.py`** — during **`combat.active`**, only **`/attack` `/block` `/item` `/flee`** plus **quicksave / save / load** /help/quit (**+ dev** slashes); **`/flee`** means standoff flee *or* combat flee depending on phase; **`/fight`** commits from a pending encounter into **`start_combat`**.
- **YELLOW (changed):** **`core/status.py`** — combat ailments (**poison/bleed/stun/weaken/guard**) with durations, ticking, and HUD banner helpers.
- **YELLOW (changed):** **`core/item_fields.py`** — **extra `effects.*` keys** (not just core stat heals) survive **`finalize_item_contract`** so antidotes/poultices stay meaningful.
- **YELLOW (changed):** **`core/inventory.py`** — consumable **`effects`** hydrate status changes (**`apply_consumable_effects`**); combat **`deduct_consumable_matched`** runs them before qty drops.
- **YELLOW (changed):** **`core/encounter_bridge.transition_to_combat_stub`** name kept for callers, **but combat is no longer a stub**: it builds a full **`state["combat"]`** blob (**no `"stub"` flag** — that field is retired).
- **YELLOW (changed):** **`ui/game_layout.py`** + **`api/server.py`** — combat ribbon (**`combat_banner`**) above World View when a bout is live; STATUS icons read timed stacks from **`STATUS_REGISTRY`** plus duration counts.
- **GREEN (added):** Demo pack items **Antidote flask**, **Sterile bandage**, **Guard draught** in **`core/state_manager.py`**.
- **GREEN (added):** Tests **`tests/test_status_combat.py`**, **`tests/test_combat_status_interaction.py`**, refreshed parser + bridge expectations.

## v0.2.4 — Hero statuses + hybrid encounter hints + HUD status strip

- **GREEN (added):** **`core/status.py`** — **`STATUS_REGISTRY`** (fatigue / weather / combat tick damage / buff families), **`player.statuses`**, apply/remove/**`clear_statuses_by_trigger`**, **`get_active_modifiers`**, HUD strings, **`tick_statuses`**, legacy **`migrate_legacy_environment_fatigue_flag`** (**`world.environment_fatigue`** → status).
- **GREEN (added):** **`core/encounters.py`** — bias table from statuses + weather + clock; deterministic roll for **`/say`/`/do`**; **`encounter_force_next`** narrator hook; RNG seed fixed for **Python 3.11+** (no tuple **`Random`** seed).
- **YELLOW (changed):** **`core/recovery.py`** — **`/sleep`** clears **`deep_sleep`** triggers and grants **`well_rested`** (no filler nap branch).
- **YELLOW (changed):** **`core/travel.py`** — start of engine travel clears **`travel`** statuses (e.g. **`sheltered`**).
- **YELLOW (changed):** **`core/state_manager.py`** (`_merge_legacy_save_shape`) + demo + **`core/character_session.py`** — run fatigue migration; new saves include empty **`player.statuses`**.
- **YELLOW (changed):** **`api/server.py`** — layout **`status_display`** / **`status_bbcode`** / **`status_fatigue`** (fatigue *family* on statuses); **`world.fatigue`** still true if legacy flag **or** any fatigue-ish status lives on the hero.
- **YELLOW (changed):** **`godot/main_layout_sync.gd`** — STATUS: name/Lv/day line + **HP / XP**, colored status BBCode row; SYSTEM **FATIGUED** reads **`layout.status_fatigue`** (not the old lone world flag story).
- **YELLOW (changed):** **`ui/game_layout.py`** terminal STATUS — same headline + XP row + colored status icons/labels (**Rich** styles), gold/dim fluff under that.
- **GREEN (added):** Tests **`tests/test_status.py`**; travel/sleep/assert tweaks in **`tests/test_world_v023.py`**.

## v0.2.3 — Adaptive clock + weather chunks + nap/sleep/travel + social seeds

- **GREEN (added):** **`core/world.py`** — **`minutes_total`** (1440-minute days), **`HH:MM`** + day line, adaptive **weather** every **≈180** game minutes, **heavy_rain** / **storm** style stat *hints* for the narrator unless **`sheltered_from_weather`**, **nemesis seed** backing list, **travel_edges** data for **`/travel`**, **minutes_passed** resolver for narration turns.
- **GREEN (added):** **`core/recovery.py`** — **`/nap`** (**1–3 h**, **≈15% HP** heal, restless flag if nowhere safe); **`/sleep`** (**+480** minutes, aggressive weather churn, **full vitals**) only when **`location_restable`**.
- **GREEN (added):** **`core/travel.py`** — Minute budget by **tier** (short/regional/**continental**) + automatic weather churn on long crossings; fuzzy **match / to_label / alias** lookups.
- **YELLOW (changed):** **`core/narrator_apply.py`** + **`core/narrator.py`** — **`state_updates`**: **`minutes_passed`**, **`location_restable`**, **`sheltered_from_weather`**, **`npc_dispositions`** (nemesis queue at hostility **≤1**); env block injected into prompts; **`__sleep__` / __nap__** narrator strips; **`narrate_and_apply(..., lock_world_time_from_llm=)`** avoids double-moving the clock after engine-handled trips/rest.
- **YELLOW (changed):** **`ui/game_session.py`** — **`/nap`**, **`/sleep`**, **`/travel`**; **`+5`** default minutes on “utility” slash commands (**not** **`/say`**, **`/do`**, sleeps, **`/travel`**, story combines, **`/give`/`/load`/start payloads** bucket).
- **YELLOW (changed):** **`core/state_manager.py`**, **`core/character_session.py`** — merges **`ensure_world`** defaults (older saves hydrate cleanly); demo bake includes **travel_edges** for **Crypt → surface / crossroads** tests.
- **YELLOW (changed):** **`api/server.py` layout** adds **`world`**: **`clock_line`**, **`weather`**, **`sky`/`weather_icon`**, **`sheltered`/`fatigue`/`location_restable`**.
- **YELLOW (changed):** **`godot/main_layout_sync.gd`** — STATUS moon/sun line + **`Day N — HH:MM`** clip; SYSTEM shows **SHELTERED / FATIGUED** cues from layout world flags.
- **GREEN (added):** Tests **`tests/test_world_v023.py`** + tweaks to **`test_api_server`**, **`test_command_parser`**, **`test_state_manager`**.

## v0.2.2 — Rarity ladder, XP (Rule C floor), leveling, stat spends

- **YELLOW (changed, prep):** **`load_game`** in **`core/state_manager.py`** — right after merge/validate, **`ensure_inventory_items`** runs so every loaded save’s pack is fully normalized (IDs, **`effects`**, **`tags`**, defaults), not only when something touches inventory later.
- **GREEN (added):** **`core/rarity.py`** — eight locked tiers (**dirt → god**) with **rank**, **hex color**, drop weights, helpers (**`roll_rarity`**, notable / mythical checks). Loot handlers can tag **found_mythical_***, **found_god_*** and nudge **`presentation["tone"]`** on god-tier finds.
- **YELLOW (changed):** **`core/inventory.py`** + **`core/item_fields.py`** — items get stable **`id`** (slug + short hash only if missing), **`effects`** (stat/restore bonuses + **`on_use`**), **`tags`** list; carry cap from STR is **`30 + STR × 2`** (spending STR updates cap via **`sync_carry`**).
- **GREEN (added):** **`core/leveling.py`** — **Rule C**: minimum **`XP_FLOOR_PER_TURN` (5)** on **`/do`** / **`/say`** narrator turns unless the model sends a higher **`xp_add`**; **`add_xp`**, **`apply_level_up`** (+3 **stat_points**, **`leveled_up_{N}`** flag), **`format_levelup_display`**.
- **YELLOW (changed):** **`core/narrator_apply.py`** + **`core/narrator.py`** — applies **`xp_add`**, announces level-ups in **`world_log`** / **`command_log`**, teaches **`/levelup`**; prompts include level / XP / pending points + loot rarity behavior.
- **YELLOW (changed):** **`core/command_parser.py`** + **`ui/game_session.py`** — **`/levelup`** (stat sheet **`presentation`**), **`/addstat`** (STR/DEX/INT/CHA/**LCK**→LUCK), **`/back`** from level-up view; **`api/server`** + demo player carry **`xp` / `xp_to_next` / `level` / `stat_points`** in layout.
- **YELLOW (changed):** **`godot/ui_crpg.gd`** + **`godot/main_layout_sync.gd`** — inventory rarity uses the **exact** tier hex values; STATUS shows XP line; SYSTEM shows amber **pending stat points** when **> 0**; World View can show **`levelup_sheet`**.
- **GREEN (added):** Tests **`tests/test_rarity.py`**, **`tests/test_leveling.py`**, **`tests/test_addstat.py`**.

## v0.2.1b — Developer warp (`--dev`) + equip hints + roadmap doc

- **GREEN (added):** **`python -m api.server --dev`** — sets **`CANON_ENGINE_DEV`**; lifespan boots **`build_dev_warp_session()`** from **`dev_warp.json`** (local, gitignored) or falls back to **`dev_warp.example.json`** (**`core/dev_warp.py`**, **`core/dev_mode.py`**).
- **GREEN (added):** Dev-only **`/godmode`** (stats → 99), **`/spawn <id>`** (small catalog); **`GET /health`** + **`layout.dev_mode`** so Godot can gate a tuck-away dev console lane later.
- **YELLOW (changed):** **`/equip <item>`** alias of **`/use`** for manuals.
- **GREEN (added):** **`core/equip_suggest.py`** — after successful equip, **command_log** **[HINT]** if a higher-rarity piece for that slot lurks in the pack (manual swap reminder, no autos).
- **YELLOW (changed):** **`canon_engine.md`** — roadmap + phase poll (**v0.2.3 · v0.2.5 · v0.3.x · v0.4.x**).
- **GREEN (added):** Tests (**`tests/test_dev_warp.py`**, **`tests/test_equip_suggest.py`**).

## v0.2.1 — Inventory depth (pack UI, weight, gear, combine, give)

- **GREEN (added):** **`core/inventory.py`** — carry vs **STR** cap, **Fatigued** when over cap, equipment slots (**weapon / torso / two accessories**), **`/inv`** text sheet, **`/inspect`**, manual **`/use`** (equip/unequip toggle or consume), **`/drop`** with **Rare+** needing **`--confirm`**, **`combinable_with`** check for **`/combine`**, **`/give … to …`** (item leaves pack first, then narrator finishes the beat).
- **YELLOW (changed):** **`core/command_parser.py`** — **`/inv`**, **`/inventory`**, **`/inspect`**, **`/use`**, **`/drop`**, **`/combine`** (two sides split by **` and `**), **`/give`** (**`to`** separates item vs recipient).
- **YELLOW (changed):** **`ui/game_session.py`** — wires the new kinds; clears **`presentation.inventory_sheet`** on non-**`/inv`** commands so World View snaps back to the story log tail.
- **YELLOW (changed):** **`core/narrator.py`** — injects **ENCUMBRANCE** into the DM prompt so physical checks tilt harder when overloaded; JSON reminder for **Fatigued** heroes.
- **YELLOW (changed):** **`core/narrator_apply.py`** — loot JSON keeps **weight / type / lore / tags / equip_slot**, not only name; always normalizes inventory + **`sync_carry`** after a reply.
- **YELLOW (changed):** **`core/state_manager.py`** + **`core/character_session.py`** — **`equipment`**, **`presentation`**, richer demo loot (incl. **Silver Wire** to test **`/combine`** with **Wolfsbane Torch**).
- **YELLOW (changed):** **`api/server.py`** — layout adds **`equipment`**, **`carry`**, **`presentation`** for the HUD bridge.
- **YELLOW (changed):** **`godot/main_layout_sync.gd`** — if **`presentation.inventory_sheet`** exists, World View (**`world_te`**) switches to inventory mode instead of **`world_log_tail`** only.
- **YELLOW (changed):** **`godot/ui_crpg.gd`** — rarity colors aligned toward the **v0.2.2** ladder (**everyday / power / god**, cleaner **mythical** gold, **dirt** near-black).
- **GREEN (added):** Tests — **`test_inventory.py`**, parser/API/state/narrator-apply bumps for the new hooks.

## v0.1.5 — World intro (`__intro__`) after character start

- **YELLOW (changed):** **`ui/game_session.py`** — on **`start_character`**, clears **`world_log`** then **`narrate_and_apply(..., "__intro__")`** so the first beat is AI (or fallback) cinematic text; return narration for the HUD beat line.
- **YELLOW (changed):** **`core/narrator.py`** — **`__intro__`** path: short opening-scene instructions, **no dice**, optional offline **`_fallback_intro`**, rolling + vector context blocks in the system prompt.
- **GREEN (added):** **`player.backstory`** on new heroes (**`core/character_session.py`**) for intro grounding.

## v0.1.6 — Input feel (bare text = say)

- **YELLOW (changed):** **`core/command_parser.py`** — lines without a leading **`/`** become **`/say …`**; friendlier empty **`/do`** / **`/say`** messages.

## v0.2.0 — Memory stack (hot / warm / cold)

- **GREEN (added):** **`core/memory_warm.py`** — rolling text in **`state["memory"]`**, refreshed every **`MEMORY_ROLL_EVERY_TURNS`** (default **10**); wired after warm file archive each turn.
- **GREEN (added):** **`core/memory_cold.py`** — ChromaDB under **`data/chroma/`**, **`retrieve_relevant_memories`** + **`index_memory_event`** (toggle **`MEMORY_COLD_ENABLED`**; **off** in tests via **`tests/conftest.py`**).
- **YELLOW (changed):** **`core/narrator.py`** — injects rolling summary + vector hits into the DM prompt; **`core/narrator_apply.py`** indexes each narration line into cold store.
- **YELLOW (changed):** **`core/state_manager.py`** — save schema includes **`memory`**; merge-defaults for older saves.
- **YELLOW (changed):** **`.gitignore`** — **`data/chroma/`**.

## v0.1.4 — `/start_character` in parser + session + HUD layout pass

- **YELLOW (changed):** **`core/command_parser.py`** — **`/start_character`** is a known command (used with the JSON **character** body on **`POST /action`**).
- **GREEN (added):** **`core/character_session.py`** — **`build_character_session_state`** (fresh crypt session: empty companions/inventory/flags, hero from payload, same tone/location/bible shell); re-exported from **`state_manager`** for one-liner imports.
- **YELLOW (changed):** **`ui/game_session.py`** — **`step_session_turn`** accepts **`character`** + **`pending_active_slot`**; applies slot after dispatch so **`/start_character`** keeps the client’s slot; intro narration: *The world stirs. [NAME] steps forward.*
- **YELLOW (changed):** **`api/server.py`** — single path through **`step_session_turn`** (no separate `/start_character` branch); **`layout_payload`** includes stamina fields for the HUD.
- **GREEN (added):** Tests — **`test_start_character`** (parser, state, API narration, game session).
- **YELLOW (changed):** **`godot/game_hud_layout.gd`** — target band heights (**90 / 430 / 110 / 44**), split **760**, removed **TEXTURE //** stamp strings from **`wrap_panel`** calls; command log taller; invoke row spacing.
- **YELLOW (changed):** **`godot/ui_panel_frames.gd`** — world **machine-well** inset padding **12px** on all sides.
- **YELLOW (changed):** **`godot/main_layout_sync.gd`** — STATUS two lines (name/level + meters), gold on **SYSTEM**, shorter EVENTS truncation.

## v0.1.3 — Character Select + `/start_character` (Godot flow)

- **GREEN (added):** **`godot/scenes/CharacterSelect.tscn`** + **`godot/character_select.gd`** — carousel over **`res://presets/characters.json`**, **SELECT** → **`POST /action`** with **`command: /start_character`** + **`character`** payload, then **GameHUD**.
- **GREEN (added):** **`godot/create_hero_modal.gd`** (**`CreateHeroModal`**) — manual **CREATE NEW** form (name, archetype, speech, stat budget / roll); **no AI** rolls characters.
- **YELLOW (changed):** **`godot/main_menu.gd`** — **Start** (and offline bypass) goes to **Character Select** instead of loading the HUD directly.
- **YELLOW (changed):** **`godot/README.md`** + **`godot/project.godot`** description — document the new boot flow.
- **GREEN (added):** **`tests/test_api_server.py`** — smoke test that **`/start_character`** updates **`layout.player.name`** from the payload.

## v0.1.2 — Resolution + HUD layout + Settings chrome

- **GREEN (added):** **`resolution_layout_fix_spec.md`** — documents 1280×720 fill, HUD band sizes, truncation rules.
- **YELLOW (changed):** **`godot/project.godot`** — **`window_width_override` / `window_height_override`** **1280×720**, stretch **`aspect=expand`** (stops letterboxed “inner box” scaling).
- **YELLOW (changed):** **`godot/boot.gd`** + **`godot/game_hud.gd`** — **`DisplayServer.window_set_size`** + **`window_set_min_size`** on enter.
- **YELLOW (changed):** **`godot/game_hud_layout.gd`** — fixed-height **top / mid / cmd / invoke** row; **split ~780** | **480**; **TEXTURE //** stamps removed on top row; RTL **scroll off + clip** for fixed panels; **`>`** invoke prefix; inventory uses **`make_rtl_body`**.
- **YELLOW (changed):** **`godot/main_layout_sync.gd`** — compact **status**, **single-line events**, short **minimap** lines; **`ui_crpg.gd`** **`inventory_bbcode`** (5 + `…+N`) and **`companions_text`** (3 + `…+N`).
- **YELLOW (changed):** **`godot/ui_settings_screen.gd`** — renamed **`form_shell`** (no **`wrap`** shadow), **MUI** backdrop + metallic form + pixel fields + START/QUIT-styled actions.
- **YELLOW (changed):** **`godot/main_menu.gd`** — **LINK** at **(8,8)**, tighter margins + taller top spacer for title vertical balance.

## v0.1.1 — Godot main menu polish (dream spec groundwork)

- **GREEN (added):** **`godot_ui_spec.md`** (project root, Godot UI master spec v0.1.0+) + **`godot/shaders/menu_ambient.gdshader`** (grain + subtle scanlines + vignette fullscreen backdrop) + **`godot/main_menu_ui.gd`** (locked palette helpers, **`NinePatchRect`** metal chip buttons + hover/press, pixel title styling).
- **GREEN (added):** **`godot/fonts/PressStart2P-Regular.ttf`** (+ **`OFL-Press_Start_2P.txt`**) — **Press Start 2P** for menu + **`ConnectionBanner`** (no HUD layout script changes beyond the banner widget).
- **YELLOW (changed):** **`godot/main_menu.gd`** — removed **TITLE CARD / TEXTURE // / ACTION** chrome; centered **CANON ENGINE** with amber/outline + deco lines; **START / SETTINGS / QUIT** as tinted nine-patch slabs; backdrop shader; modal rows use bordered flat buttons matching palette.
- **YELLOW (changed):** **`godot/ui_connection_banner.gd`** — **terminal-chip** **`StyleBoxFlat`** borders (**green / amber / red**) + pixel font; OFFLINE copy **`python -m api.server`**.

## v0.0.10a — Python: run API as a module (package imports)

- **YELLOW (changed):** Docs and Godot **LINK / offline** copy now say **`python -m api.server`** from the repo root instead of **`python api/server.py`**, because the **`__main__`** block in **`api/server.py`** runs with the **`core.*`** package on **`sys.path`** when launched as **`api.server`**.
- **YELLOW (confirmed):** **`core/__init__.py`** and **`api/__init__.py`** already exist as package markers (short docstrings; no filler logic).
- **YELLOW (fixed):** **`ConnectionBanner`** — **`add_child`** before **`set_url_display`** / outer **`set_state`** ( **`_ready()`** builds **`_lbl`** first ); refresh helpers bail if **`_lbl`** isn’t built yet.

## v0.0.10 — Godot: main menu scene flow + LINK banner (replacing stray debug strips)

- **GREEN (added):** `godot/scenes/Boot.tscn`, **`MainMenu.tscn`**, **`GameHUD.tscn`**, **`Settings.tscn`** plus **`boot.gd`**, **`main_menu.gd`**, **`game_hud.gd`**, **`game_hud_layout.gd`**, **`ui_settings_screen.gd`**, **`settings_store.gd`** (**`user://settings.cfg`**), and **`ui_connection_banner.gd`** (**`ConnectionBanner`**: CONNECTING / CONNECTED / OFFLINE / ERROR + **Retry**, military-terminal colors).
- **YELLOW (changed):** **Project boots `Boot → Main Menu → Start → HUD`** (`project.godot` **main scene** `res://scenes/Boot.tscn`). The old **HUD layout** is unchanged but built from **`game_hud_layout.gd`**; **`main_layout_sync.gd`** now targets **`hud_hint`** instead of the removed top **strip**.
- **YELLOW (changed):** **HUD overlay layers** — **LINK banner** on **CanvasLayer 210**, **pause dim** on **200**, **PS1 post** stays **128** so the chromatic wash does not bury the banner.
- **YELLOW (changed):** **Pause overlay** (**MENU button** or **`Esc`** via **`_unhandled_input`**) → Resume / Settings / Main Menu / Quit; **does not freeze** **`SceneTree`** (avoids swallowed input stuck states).
- **YELLOW (changed):** **Offline HUD** disables the invoke **`LineEdit`** and shows Retry + clear placeholder until **`GET /health`** succeeds; **`POST /action`** includes **`active_slot`** when Settings slot is valid.
- **GREEN (added):** **`ui_crpg.gd`** **`shell_stylebox_plain`** (pause/settings chrome) + **`http_result_banner_short`** for short banner lines (reserved **`Object.tr`** name conflict already fixed earlier on **`tex_rect`**).
- **YELLOW (changed):** **`main.gd`** is a thin **extends Game HUD** shim; **`main.tscn`** still works as a shortcut play scene targeting that script.

## v0.0.9 — Godot HUD: texture stamps, flavor rails, blink LEDs, CRT world frame

- **GREEN (added):** `godot/ui_hud_decor.gd` — fake **“TEXTURE // …”** silkscreen line, **flavor** subtitle next to the title (e.g. **BIO-MONITOR v2.1**), optional **blinking LED** lamp; **CRT-style** outer shell (caption strip + thick bezel + inner phosphor-tinted well) for **WORLD VIEW** only when enabled.
- **GREEN (added):** `godot/blink_led.gd` — tiny **ColorRect** “lamp” that **pulses** via `Timer` (cosmetic only).
- **YELLOW (changed):** `godot/ui_panel_frames.gd` + `godot/ui_crpg.gd` — NinePatch panels can pass **stamp / flavor / LED / CRT** into the wrapper; **`style_text_monitor`** gives the narrative **TextEdit** a flatter **phosphor** look inside the CRT frame.
- **YELLOW (changed):** `godot/main.gd` — each region gets its own decorative copy; **WORLD VIEW** uses the **CRT** path and monitor styling.
- **GREEN (added):** `godot/main_layout_sync.gd` — **HTTP → layout** refresh logic moved out of `main.gd` so that file stays **under the 300-line** project cap.
- **YELLOW (changed):** `godot/ui_panel_frames.gd` — shadow **`TextureRect`** locals renamed from **`tr`** to **`tex_rect`** so GDScript stops warning (**`SHADOWED_VARIABLE_BASE_CLASS`** — **`tr`** is Godot’s translation helper).

## v0.0.8 — Godot HUD: metallic NinePatch + recessed world well

- **GREEN (added):** `godot/ui_panel_frames.gd` — **procedural metallic/stone** 96× nine-slice texture, **`NinePatchRect`** wrappers, optional **machine-well** inner shadows (multi-layer gradients + cavity fill + inset content). **`StyleBoxTexture`** variant for **`LineEdit` / `TextEdit`** chrome.
- **YELLOW (changed):** **`godot/ui_crpg.gd`** — `wrap_panel` now builds **nine-patch** shells (accent tints **`modulate`** on the bezel). **`WORLD VIEW`** uses **`recessed = true`**.
- **YELLOW (changed):** **`godot/main.gd`** — world panel requests the recessed well.

## v0.0.7 — Asset folders (documented)

- **GREEN (added / user):** **`assets/ui/pack/`** — HUD greyscale / shader reference material (plus any subpacks you drop there). **`assets/audio/RPG Music Asset Collection/`** — music for Godot `AudioStreamPlayer` when wired. **`assets/ui/[kaz_Togo]Retro_RPG_Tileset(ver.2.0)/`** — retro tileset art for maps or UI frames.
- **YELLOW (changed):** **`assets/README.md`** — documents the three locations above and reminds that bracketed folder names must match exactly in `res://` paths.

## v0.0.6 — Godot UI pivot (spec + rules)

- **GREEN (added):** `godot_pivot_spec.md` — official direction: **Python = localhost JSON API**, **Godot = 90s CRPG window** (world view, portraits, command console, narrative log). Documents `POST /action` style contract and migration notes.
- **YELLOW (changed):** `.cursorrules` and `cursorrulescanonengine.md` — **terminal / Rich is no longer the endgame UI**; allowed to add **FastAPI+Uvicorn or Flask** only for the Godot bridge; Rich stays for dev/tests/legacy harness; **no Python desktop GUI** (Godot owns pixels).
- **GREEN (added):** `api/server.py` — **FastAPI** app with **`GET /health`** and **`POST /action`** (JSON body: `command`, optional `active_slot`). Reuses **`step_session_turn`** so saves, narrator, warm archive, and parser behave like the terminal demo. Binds are documented for **127.0.0.1** when you run Uvicorn yourself.
- **GREEN (added):** `ui/game_session.py` — **`step_session_turn`** helper (one parse + turn bump + dispatch + autosave + warm tier); terminal loop calls it so HTTP and CLI cannot drift.
- **YELLOW (changed):** `core/narrator.py` — **`narrate_and_apply`** now **returns** the narrator result dict (for JSON `narration` / `check` on `/do` and `/say`).
- **GREEN (added):** `requirements.txt` — **`fastapi`** and **`uvicorn[standard]`** for the bridge.
- **GREEN (added):** `tests/test_api_server.py` — health, `/help`, blank input, bad `active_slot` (422).
- **YELLOW (changed):** `godot/main.gd` + new `godot/ui_crpg.gd` — **CRPG panel layout** per `ui_system.md` (minimap | status | events, world + companions + inventory, command log), **colored frames**, **meter bars**, rarity **BBCode** inventory, **Enter-only** invoke bar (no Send). **HTTP** waits/retry if client still busy after `/health` (fixes bogus “network error”). **Variant typing** safe for Godot 4.6 warnings-as-errors; narrative body is **TextEdit** so log text cannot corrupt BBCode.
- **YELLOW (changed):** `godot/shaders/ps1_retro.gdshader` — **no `return` in `fragment()`** (Godot rejects that); passthrough vs PSX path uses **if / else** so the shader compiles.
- **GREEN (added):** `godot/shaders/ps1_retro.gdshader` — **PSX-style** screen pass (quantize + 4×4 dither via `hint_screen_texture`); fullscreen `ColorRect` on a **high CanvasLayer** with **mouse ignore** so UI stays clickable. Tweaks: `enabled`, `dithering`, `colors`, `dither_size` on the material.
- **GREEN (added):** **`godot/`** Godot 4 project — `project.godot`, `main.tscn`, `main.gd`: **F5** opens a window that hits **`/health`** then **`/action`**, shows narrative / command log / side panel, bottom **LineEdit** + **Send** (same `/commands` as Python). Needs **Uvicorn** running on **127.0.0.1:8765**. See **`godot/README.md`**.

## v0.0.5 — Memory tiers (warm + cold) + quicksave + usage log

- **GREEN (added):** `core/summarizer.py` — **warm tier**: every **20** turns (and `last_summary_turn` debounce), appends an AI summary block to `saves/<active_slot>_summary.md` (never deletes old blocks). Prints a dim **`[Canon Engine: archiving memory...]`** line before the API call. Same throttle env as the narrator between paid calls.
- **GREEN (added):** `core/lore.py` — **cold tier**: `saves/<slot>_bible.json` with entities + snippets; **`ingest_world_flags`** runs whenever the narrator returns `world_flags` (plus `npc_*` / `loc_*` style keys get a friendlier entity row); optional **`bible_entities`** in JSON merges too.
- **GREEN (added):** `/lore <topic>` — greps the cold bible for the **active slot** (set by `/save` / `/load`) and prints hits into the command log.
- **GREEN (added):** `/quicksave` — writes `saves/quicksave.json` without changing your active slot name.
- **GREEN (added):** Narrator system prompt now injects **warm summary tail** then **cold lore** (keyword match from the player command) **before** the in-session `world_bible` JSON — order matches your tier idea.
- **GREEN (added):** `core/openai_client.py` — one shared client builder for narrator + summarizer.
- **GREEN (added):** `core/usage_log.py` — append-only **`logs/usage.jsonl`** after successful narrator completions (per your cost rules file).
- **YELLOW (changed):** `active_slot` + `last_summary_turn` on session state; `/save` and `/load` keep **active_slot** in sync for summary/bible filenames.
- **GREEN (added):** Root **`.env`** template (empty values) next to `.env.example`; **`.gitignore`** now also ignores **`apikey.txt`** and **`logs/`**.
- **GREEN (added):** Tests `test_lore.py`, `test_summarizer.py` (mocked API, temp saves dir — still no timing-based assertions).

## v0.0.4 — Narrator (JSON DM) + `/do` / `/say`

- **GREEN (added):** `core/narrator.py` — OpenAI SDK with OpenRouter **or** direct OpenAI (`OPENROUTER_API_KEY` / `OPENAI_API_KEY`), JSON-object responses, world bible + last 5 log lines in the system prompt, **rate limit** between paid calls (`NARRATOR_MIN_INTERVAL_SECONDS`, default 1.25s).
- **GREEN (added):** `core/narrator_apply.py` — applies `narration`, `check` (logged as a check line), and `state_updates` (inventory, flags, stat deltas) to the live `state` dict only here — never inside the model callback.
- **GREEN (added):** `/do <action>` and `/say <words>` in the parser and game session; offline friendly message if no API key is set.
- **YELLOW (changed):** Demo save shape now includes `tone`, `location_name`, `world_bible`, `world_flags`, and `player.stats` / `speech_style` for DM context. Older saves get those fields filled by `load_game` before validation when possible.
- **YELLOW (changed):** After `/do`, `/say`, `/save`, or `/load`, the session **autosaves** to `autosave` (silent on success) so a long play session is less likely to die without disk backup.
- **YELLOW (changed):** `.cursorrules` and `cursorrulescanonengine.md` now spell out the narrator-vs-Python hand rule.
- **GREEN (added):** Tests: `test_narrator.py` (mocked API), `test_narrator_apply.py` (pure state). Still no sleep-based tests.

## v0.0.3 — Real JSON save/load

- **GREEN (added):** `save_game(state, path)` and `load_game(path)` in `state_manager.py`. Saves are UTF-8 JSON under `saves/`, flat files only, with **`save_version`: 1** on every write so older clients can detect newer saves later.
- **GREEN (added):** `SaveValidationError` when JSON is broken, keys are missing, or `save_version` is not `1`.
- **GREEN (added):** **Atomic saves** — data goes to `*.json.tmp` first, then `os.replace` into the real `.json`, so you never end up with a half-written main save file (important if the process dies mid-write).
- **YELLOW (changed):** `/save slot1` and `/load slot1` in the demo session; bad slots, bad files, and wrong versions log a clear `[SAVE]` / `[LOAD]` line instead of crashing.
- **YELLOW (changed):** **Ctrl+C** in the session exits without appending to session state and **without** auto-saving; anything you already `/save`d earlier is still safe on disk because of atomic replace.
- **GREEN (added):** Tests in `tests/test_state_manager.py` — round-trip, bad version, missing keys, invalid JSON, path escape, file-not-found. Still **no sleep / no timing** anywhere in the suite.
- **YELLOW (changed):** README test section calls out deterministic tests explicitly.

## v0.0.2 — Retro UI shell + demo session

- **GREEN (added):** `ui_system.md` — describes the 90s CRPG-style panel layout, colors, and rules (narrative log is append-only, UI reads state not raw AI).
- **GREEN (added):** `assets/` tree (`ui/frames`, `icons`, `backgrounds`, `portraits`, `fonts`, `audio`) with README so art and Godot hooks can land later without moving folders.
- **GREEN (added):** `build_demo_session_state()` in `state_manager.py` — in-memory Garros + skeleton + crypt minimap + starter inventory for the UI test case.
- **GREEN (added):** `ui/game_layout.py` — Rich `Layout` with minimap, status bars, events, world view, companions, inventory (rarity colors), system strip, and command log.
- **GREEN (added):** `ui/game_session.py` — game loop that clears the screen, redraws from state, and accepts `/help`, `/menu`, `/quit` (unknown commands get a friendly error).
- **YELLOW (changed):** `command_parser.py` now parses the small command set above instead of raising "not built yet."
- **YELLOW (changed):** START on the main menu jumps into the demo session; returning uses `/quit` (or Ctrl+C).
- **GREEN (added):** Preset stub for Garros in `content/presets/characters.json` (used later for real character load).
- **GREEN (added):** More smoke tests for the parser, layout export text, and the game session quit path.

## v0.0.1 — Initial scaffold + start screen

- **GREEN (added):** Project folders (`core/`, `systems/`, `ui/`, `content/`, `saves/`, `tests/`) so the game has a place to grow.
- **GREEN (added):** Stub Python files for the main game pieces (engine loop, commands, narrator, saves, memory, characters, world, etc.). They are shells for now — they raise "not built yet" if something calls them by mistake.
- **GREEN (added):** Empty preset JSON files for characters, locations, backstories, and world templates.
- **GREEN (added):** When you run `python main.py`, you get a proper terminal menu: START, SETTINGS, or CLOSE. START and SETTINGS show a "coming in v0.1" message for now; CLOSE exits nicely. Ctrl+C also exits like CLOSE.
- **GREEN (added):** `.gitignore` so secrets and junk files do not get committed; `.env.example` lists which environment variable names you will need later for API keys.
- **GREEN (added):** `.cursorrules` at the project root (same rules as `cursorrulescanonengine.md`) so Cursor follows your project rules automatically.
- **GREEN (added):** `requirements.txt` with the allowed libraries (`rich`, `openai`, `python-dotenv`, `chromadb`). Only `rich` is used for the start screen so far.
- **GREEN (added):** A small automated test that checks the start screen exits cleanly when you pick CLOSE.

## Handbook + Tutorial coverage pass (May 2026)

- **YELLOW (changed):** **`content/handbook/topics.json`** — expanded **Core Commands** with minigames (**`/lockpick`**, **`/gamble`**) and added **HUD Journal & Engine Link** topic (Journal flow + **`STARTING ENGINE`** banner meaning).
- **YELLOW (changed):** **`content/tutorial/tutorial_steps.json`** — wrap-up text now mentions minigames, Journal in pause menu, and backend auto-boot **`STARTING ENGINE`** behavior.
- **GREEN (added):** **`tests/test_handbook.py`** assertions for minigame command docs + journal/link topic.
- **GREEN (added):** **`tests/test_tutorial.py`** assertion that tutorial wrap text includes minigames, Journal, and **`STARTING ENGINE`** guidance.
