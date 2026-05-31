# Canon Engine Master Manual & Lexicon

### 1. COVER PAGE

| Field | Value |
|--------|--------|
| **Title** | Canon Engine Master Manual |
| **Current version (how to read it)** | **Which `.md` is canonical for what:** start at **`canon_engine.md` → Documentation map**. **Feature maturity** follows **`canonchanges.md`**. Save schema: **`save_version` 1** (`core/state_manager.py`). HTTP **`api_version` 1** (`api/server.py`). Track shipped UX versions via **`canonchanges.md`** narratives rather than a single repo semver. |
| **Author** | Canon Dev Team & AI Architect |
| **Date** | May 3, 2026 |

---

### 2. CLICKABLE INDEX (major chapters)

Use your viewer’s outline / search. Headings match these anchors:

1. [Cover page](#1-cover-page)  
2. [Index](#2-clickable-index-major-chapters)  
3. [Glossary](#3-the-glossary-laymans-dictionary)  
4. [Repository map](#4-repository-map-where-the-pieces-live)  
5. [Master systems log](#5-master-systems-log-the-meat)  
   - [Session, UI & command shell](#51-session-ui--command-shell)  
   - [State, saves & slots](#52-state-saves--slots)  
   - [Narration & AI client](#53-narration--ai-client)  
   - [Memory stack (warm & cold)](#54-memory-stack-warm--cold)  
   - [World, clock & procedural map](#55-world-clock--procedural-map)  
   - [Travel](#56-travel)  
   - [Encounters & standoff](#57-encounters--standoff)  
   - [Combat](#58-combat)  
   - [Party & companions](#59-party--companions)  
   - [Economy & merchants](#510-economy--merchants)  
   - [Inventory, equipment, items](#511-inventory-equipment-items)  
   - [Crafting](#512-crafting)  
   - [Stealth, scouting & traps](#513-stealth-scouting--traps)  
   - [Skills & unlocks](#514-skills--unlocks)  
   - [Factions & reputation](#515-factions--reputation)  
   - [NPCs & relationships](#516-npcs--relationships)  
   - [Quests](#517-quests)  
   - [Status effects](#518-status-effects)  
   - [Elements & damage types](#519-elements--damage-types)  
   - [Combat terrain](#520-combat-terrain)  
   - [Death, underworld & soul](#521-death-underworld--soul)  
   - [Rebirth](#522-rebirth)  
   - [Boss fights](#523-boss-fights)  
   - [Rest, nap & sleep](#524-rest-nap--sleep)  
   - [Leveling & stat spend](#525-leveling--stat-spend)  
   - [Lore query (cold bible)](#526-lore-query-cold-bible)  
   - [Character creation session](#527-character-creation-session)  
   - [Dev & warp tools](#528-dev--warp-tools)  
   - [Summarizer & usage logging](#529-summarizer--usage-logging)  
   - [Recovery & small glue](#530-recovery--small-glue)  
   - [Handbook & tutorial (meta)](#531-handbook--tutorial-meta)  
   - [Tests (what they guard)](#532-tests-what-they-guard)  
   - [Content files (data)](#533-content-files-data)  
6. [Character & stats](#6-character--stats-breakdown)  
7. [Meta: tutorial, handbook, saves](#7-the-meta-system)  
8. [Footnotes & recovery](#8-footnotes--recovery)

#### 2.1 Canonical routing (avoid duplicate write-ups)

**Single index:** **`canon_engine.md` → Documentation map** lists which `.md` owns what (bridge, guardrails, web UI notes, changelog, Cursor rules). This manual carries the **glossary**, light **repository map**, and **§5 systems log**; do **not** paste long repeats of `.env`/HTTP policy here—link using that table instead.

---

### 3. THE GLOSSARY (Layman’s dictionary)

| Term | Plain analogy |
|------|----------------|
| **RNG (random number generator)** | The **invisible dice**. The code rolls numbers (e.g. 1–20, damage dice). Same *situation* + same *seed* → same rolls → you can reproduce a “run of luck” for debugging. |
| **JSON** | The **game’s notebook pages** saved as text files humans can open. Saves under `saves/`, enemies in `content/enemies.json`, etc. The engine reads/writes these instead of a mystery binary blob. |
| **State** | The **game’s short-term memory**: one big Python dictionary while you play. HP, inventory, world flags, logs, combat stub—everything lives here until `/save` writes JSON to disk. |
| **Seed** | The **world’s recipe card**. A text seed (plus hashing) feeds the procedural generator so two runs with the same seed get the same map *shape* and tables *draws* where designed that way. |
| **Vector DB / Chroma** | **Deep wisdom on index cards**. Long story bits get turned into vectors (numbers describing meaning). When the narrator needs “what happened about X?”, the engine asks Chroma for the closest past snippets *by meaning*, not just the last paragraph. |
| **Module (`core/*.py`)** | A **toolbox drawer**—one file focused on one job (combat, economy, …). Keeps the engine maintainable. |
| **`parse_command`** | The **front desk**: turns your typed line into `{kind: ...}` so the session knows which toolbox to open. |
| **`step_session_turn`** | One **heartbeat**: parse → guards (combat/encounter) → turn counter → apply command → quests tick → world clock → autosave hooks → memory refresh. |
| **Slot** | A **labelled save jar** (`slot1`, `quicksave`, `autosave`, …). Only safe characters; Windows reserved names blocked. |
| **`run_mode` / `tutorial` blob** | **Practice field vs real season**. `run_mode: tutorial` means “don’t treat this like a campaign run” for saves and some combat rewards. |

#### Technical footnotes — Glossary

- **Determinism:** Given the same inputs and seed, pseudo-random calls repeat the same sequence (useful for tests and debugging).  
- **Embedding:** Text → vector of floats used for “similar meaning” search in Chroma.  
- **Clamping:** Force numbers into allowed min/max so saves and UI never see impossible HP.

---

### 4. REPOSITORY MAP (where the pieces live)

| Area | Role (non-tech) |
|------|------------------|
| **`core/`** | **Engine room** — rules, math, parsers, data loaders (52 Python modules at time of scan). |
| **`ui/`** | **Stage & props** — Rich terminal layout, start menu, session loop (`game_session.py`, `game_layout.py`, `start_screen.py`, `prompts.py`). |
| **`content/`** | **Printed rulebooks & catalogs** — JSON the designers edit without recompiling code. |
| **`tests/`** | **Safety drills** — automated checks (46 `test_*.py` files at time of scan). |
| **`api/`** | **HTTP bridge** — FastAPI wraps the *same* `step_session_turn` as the terminal (optional). |
| **`saves/`** | **Player vault** — one JSON per slot name. |
| **`data/chroma/`** | **Cold memory vault** (player-scoped collections). |
| **`data/chroma_npc/`** | **NPC cold memory vault** (optional, env-gated). |

#### Technical footnotes — Repository map

- **Single source of truth:** `parse_command` + `_apply_parsed` in `ui/game_session.py` define what players can actually do in-session.  
- **Import cycles avoided** by lazy imports inside some functions (e.g. tutorial building demo state).

---

### 5. MASTER SYSTEMS LOG (the “meat”)

Each subsection: friendly name, two-sentence player explanation, simple if/then logic, then a **copy-paste friendly table** of commands tied to that system.

---

#### 5.1 Session, UI & command shell

**Primary shell (today):** **Web UI (browser)** → **`python -m api.server`** → **`POST /action`** (`canon_engine.md` § HTTP bridge). **Legacy harness:** **`python main.py`** → terminal + Rich panels (same commands).

**System name:** Command shell (HTTP deck + optional terminal harness)  

**What it is:** You type slash lines into the **command deck** (or legacy terminal stream). Responses come back as narration + **`layout`** JSON for the web client—or Rich panels when using the harness.

**How it works:** If the line starts with `/`, it is treated as a **command**. If it does **not** start with `/`, the parser **prepends** `/say ` so normal dialogue still flows through the narrator path.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| *(plain text)* | Becomes `/say …` (speech) | `Hello, innkeeper.` | Same rules as `/say` |
| `/help` | Opens **handbook index** in the log | `/help` | Always |
| `/help <topic_id>` | Opens one handbook page | `/help combat_basics` | Topic must exist in `content/handbook/topics.json` |
| `/menu` `/quit` `/exit` | End session loop → return toward menu | `/menu` | Case-insensitive heads |
| `/back` | Close certain UI overlays (“presentation”) | `/back` | When overlay open |

**Technical footnotes:** **Boolean routing:** `parse_command` returns `kind`; `_apply_parsed` is a large `if/elif` chain. **Case:** command heads normalized to lower case for matching.

---

#### 5.2 State, saves & slots

**System name:** Save / load / validation  

**What it is:** Your adventure is frozen into a JSON document. Loading replaces the live session dictionary with that file’s contents.  

**How it works:** If you `/save slotname`, the engine **sanitizes** the slot (letters, digits, underscore only; length limit; Windows reserved names blocked), then writes **atomically** via a temp file. If `save_version` ≠ engine’s expected version, load **refuses** with `SaveValidationError`.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/save <slot>` | Write current state to `saves/<slot>.json` | `/save slot1` | **Blocked** in tutorial sandbox when saving disabled |
| `/load <slot>` | Replace session from file | `/load slot1` | File must exist + validate |
| `/quicksave` | Save to quicksave path | `/quicksave` | Same tutorial guard as `/save` |
| *(autosave)* | After “dirty” turns, best-effort save to the autosave slot | *(automatic)* | **Skipped** in tutorial sandbox |

**Technical footnotes:** **Atomic write:** reduces torn files on crash. **Path jail:** saves must live directly under `saves/`, no `..` tricks (`_assert_save_file_path`).

---

#### 5.3 Narration & AI client

**System name:** Narrator + OpenAI / OpenRouter client  

**What it is:** When you `/say` or `/do`, the engine asks the configured AI model to **describe** what happens, guided by world bible, memory snippets, and rules.  

**How it works:** If API keys are missing, flows that need the model surface `MissingAPIKeyError`-style handling; paid calls are rate-limited per project rules (see env vars in `core/openai_client.py` / narrator stack).

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/say <text>` | Declared speech | `/say We come in peace.` | Slash form optional if you skip the slash |
| `/do <action>` | Declared physical / narrative action | `/do Pry the sarcophagus lid.` | Triggers narrator + state hooks |

**Technical footnotes:** **Idempotency:** not guaranteed—each call is a new model completion unless tests mock the narrator.

---

#### 5.4 Memory stack (warm & cold)

**System name:** Rolling memory, warm archive, Chroma cold memory, NPC cold memory  

**What it is:** **Short memory** = last chunk of `world_log` copied into `state["memory"]["summary"]` on a schedule. **Long memory** = Chroma retrieves past lines by *meaning*. **Warm archive** = optional periodic AI-written markdown summaries per slot.  

**How it works:** If `MEMORY_COLD_ENABLED` is off-like, cold retrieval becomes a no-op. If `NPC_MEMORY_COLD_ENABLED` is on-like, NPC events index into a separate Chroma folder.

| Mechanism | What it does | Example / trigger | Restriction |
|-----------|----------------|-------------------|-------------|
| Rolling warm (`memory_warm.py`) | Refreshes in-state summary from recent `world_log` | Every N turns (`MEMORY_ROLL_EVERY_TURNS`, default 10) | No extra API by itself |
| Warm archive (`summarizer.py`) | Calls model on a cadence (`_SUMMARY_EVERY`, default 20 turns) | Long sessions | Needs API key + obeys min interval env |
| Cold memory (`memory_cold.py`) | Chroma query for narrator block | Behind narrator assembly | Env `MEMORY_COLD_ENABLED` default allows; set `0`/`false`/`no` to disable |
| NPC cold (`npc_memory_cold.py`) | Per-NPC Chroma rows | Index/query helpers | Default **off** unless env enables |

**Technical footnotes:** **Slot-scoped collections:** `sanitize_slot` prefixes Chroma collection names. **Embeddings:** Default embedding function from Chroma utils.

---

#### 5.5 World, clock & procedural map

**System name:** World blob, weather, procedural generation  

**What it is:** The **world** record tracks time (`minutes_total`), weather, location features, merchants, traps, factions snapshot, travel graph pieces, etc. Procedural generation can build a map graph and lore deck from tables.  

**How it works:** If you start a **demo** or **character** session, `apply_procedural_world` may run with a **seed-derived RNG** to fill nodes and logs. `/world` and `/map` print structured sheets.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/world` | World / run sheet | `/world` | Shell-allowed in combat/encounter shells |
| `/map` | Map / graph sheet | `/map` | Same |

**Technical footnotes:** **Deterministic worldgen:** Hash of seed string → RNG stream in boot paths (`character_session` / dev setseed).

---

#### 5.6 Travel

**System name:** Travel edges & arrival  

**What it is:** Moving between named places consumes in-world **minutes** and may reveal lore or update quest travel objectives.  

**How it works:** If `/travel <dest>` matches a known edge, time advances and location syncs; if not, you get a usage / failure message from the travel resolver.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/travel <place>` | Move along the travel graph | `/travel surface` | Blocked when combat says travel is unsafe |

**Technical footnotes:** Travel updates can touch `world.location_id` and minimap labels (`travel.py` + `worldgen` sync helpers).

---

#### 5.7 Encounters & standoff

**System name:** Pending encounter (pre-fight dialogue)  

**What it is:** Before combat, a **standoff** flag can be set with enemy intent (talk / hostile). You resolve it with talk, flee, or fight.  

**How it works:** If `pending_encounter` is true and you type a non-allowed command, the shell **blocks** you with a reminder line.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/talk` | Run encounter dialogue / rolls | `/talk` | Only meaningful with pending encounter |
| `/flee` | Attempt to flee standoff or combat | `/flee` | Context-specific success |
| `/fight` | Commit to combat from standoff | `/fight` | Starts tactical combat |

**Technical footnotes:** `encounter_bridge.py` hydrates bestiary stats into `encounter_data`; `encounter_session.py` handles talk flow.

---

#### 5.8 Combat

**System name:** Tactical combat (turn-based shell)  

**What it is:** When fighting, you choose **attack**, **block**, **item**, **flee**, look enemies, party orders, and terrain verbs. Dice rolls compare attacks vs AC, apply damage types, statuses, elements.  

**How it works:** If `combat` blob exists, only **combat shell** commands are accepted until the fight ends. If you **win** in `run_mode: tutorial`, XP / loot / gold / kill-quest credit are **skipped** by design.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/attack` | Attack default / sole target | `/attack` | In combat only |
| `/attack <n>` | Attack enemy index n | `/attack 2` | Multi-foe |
| `/block` | Defensive stance | `/block` | In combat |
| `/item <name>` | Use consumable in combat | `/item Sterile bandage` | In combat |
| `/flee` | Try to escape fight | `/flee` | In combat or standoff |
| `/look enemies` | Roster / HP-style view | `/look enemies` | In combat |

**Technical footnotes:** **d20 system:** `roll_d20` in `combat_math.py`. **STR damage:** weapon vs light damage helpers. **Enemy typing:** `enemy_type_key` drives XP tables and quest kill ids.

---

#### 5.9 Party & companions

**System name:** Companion loyalty & combat orders  

**What it is:** Allies can travel with you; in combat you may **queue orders** for them.  

**How it works:** If `/order` pattern matches `Name attack N|block|item …|flee`, the order is queued; resolver runs on AI/companion turns.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/order <name> attack <n>` | Companion attacks foe n | `/order Garros attack 1` | Combat only |
| `/order <name> block` | Companion blocks | `/order Garros block` | Combat |
| `/order <name> item <item>` | Companion uses item | `/order Garros item bandage` | Combat |
| `/order <name> flee` | Companion attempts flee | `/order Garros flee` | Combat |

**Technical footnotes:** Regex gate in `command_parser.py` ensures strict shape.

---

#### 5.10 Economy & merchants

**System name:** Shops, scavenge, rent, barter, gold  

**What it is:** Locations may expose merchants; you **buy/sell/barter**, **scavenge** junk rolls, or **rent** a room. Prices can factor **faction tier** and **NPC relationship** when a merchant NPC is linked.  

**How it works:** If a command needs a merchant context and the place has none, handlers print a blocking message.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/shop` | List merchant wares | `/shop` | Needs merchant context |
| `/buy <index>` | Buy by list index | `/buy 0` | Valid index |
| `/sell <item>` | Sell matched item | `/sell Wild Herb` | Inventory match |
| `/barter <index>` | Haggle attempt | `/barter 1` | Context rules |
| `/scavenge` | Scavenge roll / loot | `/scavenge` | Location DC / feature gates |
| `/rent` | Pay for rest / room | `/rent` | Inn / rentable site |

**Technical footnotes:** Merchant catalog in `content/merchants.json`; NPC pricing hooks in `economy.py` / `npc.py`.

---

#### 5.11 Inventory, equipment, items

**System name:** Pack, inspect, use/equip, drop, combine, give  

**What it is:** Items are dicts with weight, rarity, effects, tags. **Carry** sync prevents infinite haul. Some items grant **resistances** when worn.  

**How it works:** If `/drop` targets rare+ gear, you must append `--confirm` or the drop is refused safely.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/inv` `/inventory` | Open inventory sheet in world view | `/inv` | Not during some blocked states |
| `/inspect <item>` | Item detail | `/inspect torch` | Target must match |
| `/use <item>` `/equip <item>` | Use consumable or equip gear | `/use Antidote flask` | Skill unlocks can masquerade as “use” targets |
| `/drop <item>` | Drop to ground | `/drop Rusty Sword --confirm` | Rare+ needs `--confirm` |
| `/combine A and B` | Validates combo then narrates fuse | `/combine herb and vial` | Narrator-led resolution |
| `/give <item> to <target>` | Hand item to NPC | `/give torch to guard` | Inventory + narration |

**Technical footnotes:** **Normalization** in `inventory.py` / `item_fields.py`. **Rarity rolls** use `rarity.py`.

---

#### 5.12 Crafting

**System name:** Recipes & crafting rolls  

**What it is:** Known recipes live in state + `content/recipes.json` / craft catalog. Crafting spends mats and rolls skills.  

**How it works:** If you `/craft` during combat, the session says hands are full.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/craft list` | Known recipes | `/craft list` | Safe shell |
| `/craft <recipe_id>` | Attempt craft | `/craft crude_antidote` | Not in combat |

**Technical footnotes:** Successful craft emits quest progress event `craft_item` where applicable.

---

#### 5.13 Stealth, scouting & traps

**System name:** Scout / stealth / detect / disarm  

**What it is:** You can **scout** an area, attempt **stealth**, **detect** traps, and **disarm** by trap id. Combat may apply surprise hooks.  

**How it works:** If stealth breaks (e.g. loud speech), status/log lines explain it (`stealth.py`).

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/scout` | Scout resolution | `/scout` | Shell rules |
| `/stealth` | Stealth attempt | `/stealth` | Shell rules |
| `/detect` | Trap detection | `/detect` | Shell rules |
| `/disarm <trap_id>` | Disarm specific trap | `/disarm spike_trap` | Needs trap id |

**Technical footnotes:** Trap definitions in `content/traps.json`; terrain features in `content/terrain_features.json`.

---

#### 5.14 Skills & unlocks

**System name:** Skill trees & active skill uses  

**What it is:** Player has skill points and unlockable nodes (`content/skills_trees.json`). Some “uses” in inventory are actually **skill activations** when the id matches an unlocked skill.  

**How it works:** If `/unlock` references unknown id, unlock function logs failure.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/skills` | Show skills sheet | `/skills` | — |
| `/unlock <skill_id>` | Spend points to unlock | `/unlock power_strike` | Needs available points |

**Technical footnotes:** `skills.py` ensures trees on player blob.

---

#### 5.15 Factions & reputation

**System name:** Faction standing  

**What it is:** Factions have reputation tiers affecting prices, quest flavor, etc.  

**How it works:** If you `/reputation` on unknown id, you get a friendly not-found style message from formatters.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/factions` | List factions | `/factions` | — |
| `/reputation <faction_id>` | Detail one faction | `/reputation iron_guild` | Valid id |

**Technical footnotes:** `content/factions.json` seeds labels; abandoning quests can hit rep (`factions.py`).

---

#### 5.16 NPCs & relationships

**System name:** NPC registry, sheets, gift & threaten  

**What it is:** NPCs have roles, rapport, memory summaries, and can affect shops and quests.  

**How it works:** If you `/gift` or `/threaten`, quest hooks may update alongside relationship deltas.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/npcs` | Who is here | `/npcs` | Location-scoped |
| `/npc <npc_id>` | NPC detail sheet | `/npc merchant_a` | Valid id |
| `/gift <npc_id> <item>` | Gift flow | `/gift npc_a torch` | Inventory |
| `/threaten <npc_id>` | Threaten flow | `/threaten npc_b` | — |

**Technical footnotes:** `npcs_seed_templates.json` feeds generation; optional cold NPC memory under env.

---

#### 5.17 Quests

**System name:** Dynamic quests (templates, progress, turn-in)  

**What it is:** Quests are generated from templates, tracked in state, can expire, and pay rewards via `quest_rewards.py`.  

**How it works:** If a quest deadline passes, `fail_expired_quests` runs each turn and appends log lines.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/quests` | List active / available | `/quests` | — |
| `/quest <quest_id>` | Inspect one | `/quest q_deliver_01` | — |
| `/accept <quest_id>` | Accept offer | `/accept q_hunt_02` | Must be offered |
| `/abandon <quest_id>` | Drop quest | `/abandon q_hunt_02` | Rep hit |
| `/turnin <quest_id>` | Complete at hub | `/turnin q_deliver_01` | Objectives must be met |

**Technical footnotes:** Kill/craft/travel events funnel into `update_quest_progress`.

---

#### 5.18 Status effects

**System name:** Buffs, debuffs, durations  

**What it is:** Statuses are typed dicts (families: buff, fatigue, weather, combat, …) with icons/labels and durations.  

**How it works:** If a status trigger says “clear on combat end,” `clear_statuses_by_trigger` runs when combat ends.

| Mechanism | What it does | Example | Restriction |
|-----------|----------------|---------|-------------|
| *(combat / items / traps)* | Apply/remove statuses | Poison, bleeding, cover buffs | See individual commands |

**Technical footnotes:** Registry in `status.py` with `STATUS_REGISTRY` for UI coloring (`game_layout.py`).

---

#### 5.19 Elements & damage types

**System name:** Typed damage & resistances  

**What it is:** Damage has a **type** (`physical`, `fire`, `frost`, `lightning`, `holy`, `void`). Armor/items/enemies may resist.  

**How it works:** If an unknown type string arrives, normalizer falls back to `physical`.

| Data | What it does | Example | Restriction |
|------|----------------|---------|-------------|
| Enemy `resistances` | Multiply incoming typed damage | `{"fire": 0.5}` | JSON in bestiary rows |
| Player + torso armor | Adds resist map | Wearing resist gear | Merged in `elements.py` |

**Technical footnotes:** Weather synergy hooks live in `elements.py` comments (rain vs fire, etc., per implementation).

---

#### 5.20 Combat terrain

**System name:** Cover, climb, interact  

**What it is:** During fights, local features (cover, high ground, barrels) can be **used tactically**.  

**How it works:** If the location lacks the feature, the terrain module answers “no cover here” style.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/cover` | Take cover | `/cover` | Combat + feature |
| `/climb` | Seek high ground | `/climb` | Combat + feature |
| `/interact <feature_id>` | Interact e.g. barrel | `/interact oil_barrel` | Combat |

**Technical footnotes:** `terrain.py` + `terrain_features.json`.

---

#### 5.21 Death, underworld & soul

**System name:** HP zero pipeline, underworld navigation, soul sheet  

**What it is:** Taking lethal damage can start **death saves** or underworld flows; soul commands expose metaphysical inventory.  

**How it works:** If HP ≤ 0 after combat defeat, `death.py` may chain into underworld states.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/soul` | Soul / underworld sheet | `/soul` | State-gated messaging |
| `/remember <memory_id>` | Soul-memory action | `/remember echo_1` | Usage string |
| `/anchor <target>` | Anchor soul | `/anchor self` | Usage string |
| `/bribe <npc_id>` | Underworld bribe | `/bribe ferryman` | Usage |
| `/ascend` | Ascend underworld layer | `/ascend` | Valid state |
| `/descend` | Descend | `/descend` | Add word `force` to set forced descend (`/descend force`) |
| `/underworld enter` | Enter while alive (soul path) | `/underworld enter` | Requires soul path |
| `/death_continue` | Continue death flow | `/death_continue` | Death state |
| `/death_yield` | Yield to fate | `/death_yield` | Death state |

**Technical footnotes:** `underworld.py`, `death.py`; `/descend force` sets `force: True` in parse result.

---

#### 5.22 Rebirth

**System name:** Rebirth paths & carried legacies  

**What it is:** After certain mythic milestones, **rebirth** paths adjust future modifiers (LCK/STR carry, blessings, curses).  

**How it works:** If `/rebirth` path token not in allowed set, rebirth module rejects.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/rebirth <path>` | Choose rebirth path | `/rebirth standard` | One of: `standard`, `permanent`, `ascension`, `descension`, `purgatory_negotiated` |

**Technical footnotes:** `rebirth.py`; LCK modifier stacking with `permanent_lck_modifier` in stats.

---

#### 5.23 Boss fights

**System name:** Boss phases & rewards  

**What it is:** Certain enemies are flagged **boss**; extra hooks run on defeat (loot bias, quest flags, `world_flags.defeated_named_boss`).  

**How it works:** If boss dies, `boss.py` may emit special log lines and set progression flags.

| Mechanism | What it does | Example | Restriction |
|-----------|----------------|---------|-------------|
| Boss combat | Uses `is_boss` / `boss_id` fields | Scripted bosses in `content/bosses.json` | Not every enemy |

**Technical footnotes:** Boss JSON separate from trash mobs in `enemies.json`.

---

#### 5.24 Rest, nap & sleep

**System name:** Short vs long rest  

**What it is:** **Nap** heals a little; **sleep** heals more and may require a safe inn / camp. CON modifier scales healing.  

**How it works:** If world says “not restable,” sleep refuses.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/nap` | Short rest + time advance | `/nap` | World rules |
| `/sleep` | Deep rest | `/sleep` | Rest-safe locale |

**Technical footnotes:** Heal formulas `nap_heal_amount` / `sleep_heal_amount` in `stats.py`.

---

#### 5.25 Leveling & stat spend

**System name:** XP, levels, `/levelup`, `/addstat`  

**What it is:** You earn XP (combat, quests, …). Crossing threshold levels you up and grants **stat points** and **skill points**.  

**How it works:** If `/addstat` targets unknown stat or you have 0 points, you get a system message.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/levelup` | Open level-up panel | `/levelup` | Must have pending level / points rules |
| `/addstat STR` | Spend one point | `/addstat CON` | STR, DEX, INT, CHA, CON, LCK (LUCK alias → LCK) |

**Technical footnotes:** `xp_to_next = level * 100` baseline (`leveling.py`).

---

#### 5.26 Lore query (cold bible)

**System name:** `/lore` Chroma-backed topic fetch  

**What it is:** Pulls a **cold lore** text block for a topic label tied to your save slot.  

**How it works:** If `/lore` missing topic, usage error.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/lore <topic>` | Query cold lore | `/lore crypt` | Needs topic string |

**Technical footnotes:** `lore.py` uses slot + topic.

---

#### 5.27 Character creation session

**System name:** `/start_character` (API-first)  

**What it is:** Replaces live session with a hero built from a **character JSON** (tests or API). Runs procedural world boot from seed/name.  

**How it works:** If payload missing in terminal, error line explains API expectation.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/start_character` | Rebuild session from character dict | *(API body)* | Terminal needs API payload |

**Technical footnotes:** `character_session.py` builds the blob; intro narration special-cased.

---

#### 5.28 Dev & warp tools

**System name:** Developer warp session & cheats  

**What it is:** When **dev mode** is on, extra commands exist to test combat, items, and world re-seeding.  

**How it works:** If dev mode off, `/godmode` etc. parse as **unknown** command.

| Command | What it does | Example use | Restriction |
|---------|----------------|-------------|-------------|
| `/godmode` | Pump stats | `/godmode` | Dev only |
| `/spawn <id>` | Spawn test item | `/spawn golden_staff` | Dev only |
| `/setseed <text>` | Regenerate procedural world | `/setseed demo-2` | Dev only; **breaks continuity** (warned in logs) |

**Technical footnotes:** `dev_mode.py` reads env; `dev_warp.py` holds spawn tables.

---

#### 5.29 Summarizer & usage logging

**System name:** Warm summary files + token/cost logging  

**What it is:** Every so many turns, optional call writes markdown summary per slot; usage logger records chat calls for budgeting.  

**How it works:** If API missing, summarizer catches and logs gracefully.

| Artifact | What it does | Where | Restriction |
|----------|----------------|-------|-------------|
| `*_summary.md` | Long-form rolling AI summary | `saves/` | Slot-based |
| `usage_log` | Chat usage records | `usage_log.py` | Env-driven |

---

#### 5.30 Recovery & small glue

**System name:** `recovery.py`, `engine.py`, `rarity`, `equip_suggest`, `enemy_ai`, `item_fields`  

**What it is:** Helper modules for rest narration hooks, rare item rolling, equip suggestions, AI turn picks, field validation.  

**How it works:** These are mostly **called by** combat/economy—not direct player commands.

**Technical footnotes:** Treat as **sub-devices** invoked internally.

---

#### 5.31 Handbook & tutorial (meta)

See **Section 7** for the full meta picture; commands also listed in **5.1** and here:

| Command | What it does | Example | Restriction |
|---------|----------------|---------|-------------|
| `/tutorial` | Current tutorial step header | `/tutorial` | Tutorial sandbox only |
| `/tutorial next` | Preview next step | `/tutorial next` | Tutorial only |
| `/tutorial reset` | Reset step machine + clear standoff/combat | `/tutorial reset` | Tutorial only |
| `/tutorial exit` | Quit to menu | `/tutorial exit` | Tutorial only |

**Technical footnotes:** Steps JSON: `content/tutorial/tutorial_steps.json`. Handbook JSON: `content/handbook/topics.json`.

---

#### 5.32 Tests (what they guard)

Automated tests live in `tests/`. They do **not** ship to players but **prove** the engine behaves. Examples mapped to systems:

| Test file (sample) | Guards |
|---------------------|--------|
| `test_combat.py`, `test_layout_combat.py`, … | Combat math, UI banners |
| `test_economy.py` | Shop / scavenge |
| `test_quests_*.py` | Quest generation / progress / turn-in |
| `test_worldgen.py` | Procedural graph |
| `test_handbook.py`, `test_tutorial*.py` | Help + sandbox saves |
| `test_npc_*.py` | NPC + cold memory |
| `test_death.py`, `test_underworld.py`, `test_rebirth.py` | Death pipeline |
| `test_summarizer.py` | Warm archive smoke |
| `test_api_server.py` | HTTP bridge parity |

**Technical footnotes:** Run `python -m pytest tests -q` from project root.

---

#### 5.33 Content files (data)

| File / folder | Purpose |
|---------------|---------|
| `content/enemies.json` | Bestiary entries (incl. tutorial dummy) |
| `content/bosses.json` | Boss scripts |
| `content/merchants.json` | Catalogs / offers |
| `content/recipes.json`, `craft_catalog.json` | Crafting |
| `content/factions.json` | Faction labels |
| `content/skills_trees.json` | Skill web |
| `content/traps.json`, `terrain_features.json` | Hazards / interactables |
| `content/worldgen_tables.json` | Procedural weights |
| `content/quest_templates.json` | Quest patterns |
| `content/npcs_seed_templates.json` | NPC generation |
| `content/monster_parts.json` | Parts / salvage economy |
| `content/presets/*.json` | Optional character/world/backstory presets |
| `content/handbook/topics.json` | Player handbook pages |
| `content/tutorial/tutorial_steps.json` | Tutorial checklist |

---

### 6. CHARACTER & STATS BREAKDOWN

**The six core stats (STR, DEX, INT, CHA) — what players feel**

| Stat | Plain English effect | In-engine touchpoints (non-exhaustive) |
|------|----------------------|----------------------------------------|
| **STR** | **Hard hits & carry.** Bigger muscle → more melee damage bonus, shove doors, wear heavy kit. | Weapon damage bonus (`calculate_damage_*` + STR mod); encumbrance synergy via inventory sync. |
| **DEX** | **Hands & feet.** Quick feet → harder to hit, better flee rolls, nimble tasks. | Player AC bonus term; flee contests pack DEX (`combat.py`). |
| **INT** | **Book smarts & pattern spotting.** Useful when puzzles, traps, or magic checks ask for mind over muscle. | Skill / trap / magic hooks consult INT where coded. |
| **CHA** | **Presence & tongue.** Talk people down, haggle, lead—when the engine checks “how convincing?” | Social / faction-adjacent rolls in encounter & economy flows. |

**CON (Constitution) — body & grit**

- **Max HP** = `50 + CON × 5` (+ tiny rebirth bonus fields if present). Think of CON as **how big your health bar is painted**.  
- **Nap / sleep healing** scales with the **CON modifier table** (`nap_heal_amount`, `sleep_heal_amount`). Better CON → better rest recovery.

**LCK (Luck) — fortune curve**

- Uses the **same modifier table** as CON (`score_to_modifier`).  
- **Loot / rarity bias** in combat victory uses LCK (see combat victory loot roll messaging).  
- Optional **luck decay** (`world_bible.luck_decays`): extreme rolls can **nudge LCK down on nat20** or **up on nat1** (`apply_lck_decay`)—the idea that fortune is fickle, implemented as small stat drift.  
- **Rebirth** can add a permanent LCK modifier stored on the player (`get_lck_modifier` adds `permanent_lck_modifier`).

**“Earned greatness” gate (narrator bias, not a command)**

- If level ≥ 10, defeated a named boss flag set, honored+ faction rep exists, and optional bible rebirth requirement met, `earned_greatness_threshold_met` is true—mainly for **narrator acknowledgment**, not a player slash command.

#### Technical footnotes — Stats

- **Table modifiers** for CON/LCK are **not** the classic `(score−10)/2` curve; they use discrete steps in `score_to_modifier`.  
- **Clamping:** Stats forced into **3–24** (and STR/DEX up to 30 in some combat reads) to stop insane saves.  
- **LUCK vs LCK:** Legacy `LUCK` mirrors `LCK` for older saves/UI.

---

### 7. THE META SYSTEM

**Tutorial sandbox**

- **Start:** Main menu → Tutorial loads `build_tutorial_session_state()` (`core/tutorial.py`).  
- **State flags:** `run_mode: tutorial`, `tutorial.active: true`, `tutorial.allow_save: false` (until you change design).  
- **Safety:** `/save`, `/quicksave`, autosave **do not** write campaign slots; combat wins **skip** XP/loot/gold/kill-quest credit.  
- **Guide:** `content/tutorial/tutorial_steps.json` + yellow **header strip** in UI (`game_layout.py`).  
- **Commands:** `/tutorial`, `/tutorial next`, `/tutorial reset`, `/tutorial exit`.

**Handbook (`/help`)**

- **Index:** `/help` prints `[HANDBOOK]` lines from `content/handbook/topics.json`.  
- **Topic:** `/help <id>` prints one topic’s bullets + examples.  
- **Menu:** Start screen “Handbook” opens an interactive browser (`ui/start_screen.py`).

**Saving / loading logic**

- **Slots** = filenames under `saves/`.  
- **Validation** = `save_version` must match `CANON_SAVE_VERSION` (currently **1**).  
- **Autosave** triggers on dirty turns in campaign; skipped in tutorial sandbox.

#### Technical footnotes — Meta

- **Deep copy:** Tutorial clones demo state then overwrites fields—prevents accidental shared references.  
- **API parity:** HTTP bridge hits the same parser + session step as terminal.

---

### 8. FOOTNOTES & RECOVERY

**If something breaks**

1. **Read the last lines of `command_log`** in the UI—they are the engine’s own voice.  
2. **Check `save_version`** inside your JSON save if load fails (engine mismatch).  
3. **Flip memory envs:** disable cold memory (`MEMORY_COLD_ENABLED=0`) or NPC memory (`NPC_MEMORY_COLD_ENABLED=0`) to rule out Chroma issues.  
4. **Run tests:** `python -m pytest tests -q` — if red, the regression is real, not “bad luck.”  
5. **Tutorial stuck?** `/tutorial reset` clears combat + pending encounter and returns to step 1.

**Global technical vocabulary**

| Term | One-line meaning |
|------|------------------|
| **Determinism** | Same seed + same calls ⇒ same random draws. |
| **Boolean gate** | `if pending_encounter: block command` style checks. |
| **Clamping** | `max(min_val, min(max_val, x))` keeps numbers legal. |
| **Atomic IO** | Write temp file then rename so you never load half a save. |
| **Slot sanitization** | Lowercase, allowed charset, reserved Windows names rejected. |

---

*End of Canon Engine Master Manual — generated from an audited snapshot of `core/`, `ui/`, `content/`, and `tests/` as of May 3, 2026. If a command stops working, trust `core/command_parser.py` + `ui/game_session.py` over this PDF.*
