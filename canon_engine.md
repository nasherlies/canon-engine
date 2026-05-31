# CANON ENGINE
**A personal AI-powered text-based infinite RPG engine.**
Owner: [you] | **Python** = rules / saves / narrator; **localhost web UI** = primary player shell (browser). AI: API-key driven (no subscription middleman).

---

## 🎯 CORE VISION
A single-player, AI-narrated, infinite RPG sandbox where the player can drop a character of ANY archetype into ANY setting and the world stays internally consistent. Inspired by tabletop DnD, One Piece, Adventure Time, Solo Leveling, DBZ, Naruto, Mob Psycho, Ben 10, Full Metal Alchemist, Spirited Away, Regular Show, Golden Boy, One Punch Man, COD, MMA, and more — genre-fluid but lore-locked.

This is a **personal project**. No SaaS bloat. No subscription wrappers. API keys come straight from the source (OpenAI, Anthropic, OpenRouter, etc.) and live in a local `.env` file.

---

## 📚 Documentation map (single index)

Use this table as the routing authority. **Prefer linking here instead of repeating** the same setup, bridge, or policy text in other files.

| Need | Canonical file |
|------|----------------|
| Game design, vision, flows, clocks, combat blob (**design law**) | `canon_engine.md` (this file) |
| `POST /action` JSON, localhost bridge | `canon_engine.md` § HTTP bridge + `api/server.py` |
| Glossary + long §5 systems log (operator companion) | `CANON_ENGINE_MASTER_MANUAL.md` |
| Layout guardrails (anchors / avoid layout fights — apply to web as CSS/grid discipline) | `ui_guardrails.md` |
| 90s panel *aesthetic* wireframe (**reference**, not shipped layout authority) | `ui_system.md` |
| Resolution / legacy split-HUD pixel targets (**may differ** from anchor-only cinematic HUD) | `resolution_layout_fix_spec.md` |
| Repo quickstart | `README.md` |
| Grand narrative: spine, pods, saga flags | `narrative_saga_framework.md` |
| Planner milestones | `roadmap.md` |
| Layman changelog | `canonchanges.md` |
| API keys, cost discipline, usage log path | `# API KEY & COST MANAGEMENT RULES.txt` |
| Cursor agent rules | **`.cursorrules`** (repo root only) |

---

## 🧠 RECOMMENDED AI MODEL (cost vs. quality)
| Model | Cost (approx) | Why |
|---|---|---|
| **Claude 3.5 Haiku** (Anthropic) | ~$0.80/1M input, $4/1M output | Cheapest GOOD narrative model. Great for long-context storytelling. |
| **GPT-4o-mini** (OpenAI) | ~$0.15/1M input, $0.60/1M output | DIRT cheap. Solid narrative. Use this as default. |
| **DeepSeek V3** (via OpenRouter) | ~$0.27/1M input, $1.10/1M output | Insanely cheap, surprisingly creative. Great fallback. |
| **Claude Sonnet 4.5** | $3/1M input, $15/1M output | Premium "boss fight" / lore-critical moments only. |

**Default recommendation:** Start with `gpt-4o-mini` for everyday narration, escalate to `Claude Sonnet 4.5` only for major story beats / world generation. Use OpenRouter as a single API gateway so you can swap models without rewriting code.

---

## 🔌 HTTP BRIDGE — LOCALHOST WEB UI ↔ PYTHON (FASTAPI — INTENTIONAL, PERMANENT)

The engine runs as **Python** (rules, saves, narration, combat). The **shipped player surface** is a **browser** (or other HTTP client) on **`127.0.0.1`**, talking to the same session pipeline as the dev harness.

- **`FastAPI`** + **`Uvicorn`** in **`api/`** serve **JSON-in / JSON-out** on localhost (e.g. **`POST /action`**, **`GET /health`**, handbook/journal routes). **Route shapes and response fields** are defined in **`api/server.py`**; contract tests live under **`tests/test_api_server.py`** and **`tests/test_playability_smoke.py`**.
- Scope stays **machine-local**: not a deployed public website unless you deliberately expose it.
- This stack is documented in **`.cursorrules`** as a **permanent exception** to generic “avoid web frameworks in engine code” wording; it must **not** be removed casually without a replaced, approved transport contract.

---

## Tactical combat blob (`state["combat"]`) — canonical shape (v0.3.x)

The shipped engine uses **`core/combat.py`** with **free functions** and a **plain dict** on **`state["combat"]`**, **not** a **`CombatSession`** class. As of **v0.3.2**, the roster is **`state["combat"]["enemies"]`**: a list of foe dicts (**`id`**, **`name`**, **`type`**, **`hp`**, **`max_hp`**, **`ac`**, **`str`**, **`dex`**, **`statuses`**, **`intent`**, **`loot_bias`**, **`ability_cooldown`**) plus **`active_enemy_index`**, **`player_block_bonus`**, **`round`**, **`turn`**. Any older sketches or spreadsheets that referenced a **`CombatSession`** type or separate **`CombatSession`** file described the **same responsibilities**—the authoritative names live in **`core/combat.py`** (**`resolve_player_attack`**, **`resolve_player_block`**, **`resolve_combat_flee`**, **`enemy_turn_resolve`**, etc.). When in doubt, read the implementation, not the retired naming.

---

## World clock — time authority

**`minutes_total`** and coupled weather churn are advanced **only** through **`core.world.apply_time_passed`**. **`advance_world_time`** is the normal **facade** for callers (**it forwards into `apply_time_passed`** — same mechanics). If a dev protocol text says “call **`apply_time_passed`** only,” read that as **no ad hoc `minutes_total` writes** in feature code—not a ban on **`advance_world_time`**.

---

## 🗂️ PROJECT STRUCTURE
canon_engine/
├── .env # API keys (gitignored)
├── .cursorrules # Cursor AI behavior rules
├── canon_engine.md # THIS FILE
├── main.py # Entry point
├── core/
│ ├── engine.py # Main game loop
│ ├── command_parser.py # /say /do /look etc.
│ ├── narrator.py # AI narration calls
│ ├── state_manager.py # Save/load world state
│ └── memory.py # Long-term lore memory (vector DB or JSON)
├── systems/
│ ├── character.py # Player & NPC data
│ ├── inventory.py # Items + rarity
│ ├── companions.py # Followers, relationships
│ ├── world.py # World rules, setting consistency
│ ├── shops.py # Vendors, currencies
│ ├── minigames.py # Combat, dice, skill checks
│ └── lore.py # Persistent lore entries
├── content/
│ ├── presets/
│ │ ├── characters.json # Preset characters
│ │ ├── locations.json # Preset starting locations
│ │ ├── backstories.json
│ │ └── worlds.json # Genre/setting templates
│ └── languages/ # Pirate speak, western drawl, etc.
├── saves/ # JSON save files per playthrough
└── ui/
├── start_screen.py # Start / Settings / Close
└── prompts.py # Reusable text prompts
---

## 🎮 GAME FLOW

### 1. START SCREEN
- **Title:** CANON ENGINE
- **Options:**
  - `START` → go to character selection
  - `SETTINGS` → AI model, API key, narration verbosity, language style, autosave interval
  - `CLOSE` → exit

### 2. CHARACTER SELECTION
- **Option A:** Load existing save
- **Option B:** Pick from presets (Garros the Western Knight, etc.)
- **Option C:** Create new character

### 3. CHARACTER CREATION MODULES
Every character MUST have:
- **Name**
- **Archetype** (knight, mage, alien, businessman, fighter, skeleton, etc. — open input + presets)
- **Appearance** (text-based: hair, build, scars, clothing, distinguishing marks)
- **Personality** (traits, flaws, quirks — affects AI dialogue)
- **Speech style** (normal, pirate, western drawl, formal, gen-z, robotic, broken-english, etc.)
- **Stats** (STR, DEX, INT, CHA, LUCK — DnD-inspired, 1–20 scale)
- **Skills/Abilities** (combat, magic, tech, social, etc.)
- **Starting Inventory** (auto-genned from archetype + setting)
- **Backstory** (preset or custom — AI generates 3 options based on character + setting)
- **Goals/Motivation** (what drives them)

### 4. WORLD/SETTING SELECTION
**Mix-and-match system:**
- Pick a **base genre** (medieval fantasy, sci-fi, modern, post-apoc, anime-shonen, slice-of-life, horror, etc.)
- Pick a **starting location** (supermarket, WW2 trench, magical academy, pirate ship, space station, etc.)
- Pick a **collision factor** (the "out of place" element — e.g., knight in supermarket)

The AI then generates a **World Bible** — a locked document of world rules (magic system? tech level? gods? politics?) that MUST be referenced in every subsequent narration to maintain consistency.

### 5. BACKSTORY HOOKS (auto-genned based on character + world)
Examples:
- "Your wife just left you and a portal opened in your computer screen."
- "You woke up in a body that isn't yours."
- "The kingdom fell while you slept in the crypt."
- "You touched the wrong artifact at the museum."

3 options presented, plus "custom input" + "surprise me."

---

## ⌨️ COMMAND SYSTEM (forward slash)

### Player Commands
| Command | Use |
|---|---|
| `/say <text>` | Speak dialogue |
| `/do <action>` | Perform an action |
| `/look [target]` | Examine surroundings or object |
| `/move <direction/place>` | Travel |
| `/attack <target>` | Combat action |
| `/use <item>` | Use inventory item |
| `/inv` | Open inventory |
| `/stats` | View character sheet |
| `/companions` | View followers |
| `/lore [topic]` | Query the world bible |
| `/save [slotname]` | Save game |
| `/load [slotname]` | Load game |
| `/help` | Command list |

### Admin / Edit Mode (you only)
| Command | Use |
|---|---|
| `/admin` | Toggle admin mode (password gated in `.env`) |
| `/edit <entity> <field> <value>` | Modify any entity |
| `/spawn <thing>` | Force-create item/NPC/location |
| `/retcon <event>` | Rewrite a past story beat |
| `/model <name>` | Hot-swap AI model |
| `/verbose <0-3>` | Narration depth |
| `/lang <style>` | Force NPC speech style |
| `/dump` | Print current world state |

---

## 💎 ITEM RARITY SYSTEM
| Tier | Color | Drop Rate | Example |
|---|---|---|---|
| Dirt | Brown | 50% | Rusty dagger |
| Common | Gray | 25% | Iron sword |
| Uncommon | Green | 12% | Enchanted blade |
| Rare | Blue | 7% | Frostbrand |
| Epic | Purple | 4% | Shadowfang |
| Legendary | Gold | 1.8% | Excalibur replica |
| Mythical | Crimson | 0.2% | A literal star, weaponized |

Items have: name, tier, description (AI-genned), stats, abilities, lore entry (auto-added to world bible).

---

## 👥 COMPANION SYSTEM
- Recruit via story events, dialogue, quests, debt, blackmail, friendship, etc.
- Each companion has: **loyalty** (-100 to +100), **personality**, **skills**, **backstory**, **relationship status**.
- Companions can **learn** (e.g., crypt skeleton learning to speak via mage tutoring).
- Companions can **die permanently** (toggleable in settings).
- Companions can **leave** if loyalty drops too low.
- Companion-companion relationships also tracked.

---

## 🏪 SHOPS & ECONOMY
- Currency adapts to setting (gold, credits, ration tickets, beli, zenny, USD).
- Shops have personalities, inventory rotation, haggling minigame.
- Black markets, traveling merchants, NPC trades, theft mechanic (with consequences).

---

## 🎲 MINIGAMES
- **Combat:** Turn-based, stat + dice (d20) + ability modifiers. Narrated.
- **Skill checks:** /do triggers a hidden roll if outcome uncertain.
- **Dialogue duels:** persuasion battles vs important NPCs.
- **Crafting / cooking / fishing:** optional sandbox loops.
- **Card / dice gambling** at taverns.

---

## 📚 LORE & MEMORY (THE HARD PART)
**The biggest failure mode of the original ChatGPT version was context window loss.** Solution:

### Three-Tier Memory
1. **Hot context** (last ~20 turns) → fed directly into prompt.
2. **Warm summary** → after every 20 turns, AI auto-summarizes and stores in `saves/<slot>/summary.md`.
3. **Cold lore (vector DB)** → all named entities (NPCs, items, locations, events) stored in a local vector database (use `chromadb` — free, runs locally). Queried by relevance before each narration.

### The World Bible
A locked `world_bible.json` per save containing:
- World rules (magic? tech? physics quirks?)
- Active NPCs + descriptions
- Visited locations
- Key events (timeline)
- Active quests
- Companion roster
- Player relationships

**Every AI narration call MUST inject relevant world bible entries** so consistency holds across hundreds of turns.

---

## 🌐 GENRE / IP INSPIRATION REFERENCE
The engine should be able to riff on (but not direct-copy) tones from:
- **One Piece** — adventurous, sea-faring, devil fruit logic
- **Adventure Time** — whimsical post-apoc fantasy
- **Solo Leveling** — leveling/dungeon system
- **DBZ / Naruto** — power scaling, ki/chakra
- **Mob Psycho / One Punch Man** — overpowered protagonist subversion
- **Full Metal Alchemist** — equivalent exchange magic
- **Spirited Away** — spirit world / liminal spaces
- **Regular Show / Golden Boy** — slice-of-life absurdism
- **Ben 10** — transformation mechanics
- **Call of Duty / MMA** — tactical / brutal combat

Player can flag tone in settings (`/tone shonen`, `/tone gritty`, `/tone whimsical`).

---

## 🗣️ LANGUAGE / SPEECH STYLES (fun layer)
Configurable per character / NPC:
- Pirate speak ("Arrr, ye scurvy dog!")
- Western drawl (Garros-style)
- Shakespearean
- Gen-Z brainrot
- Formal Victorian
- Robotic monotone
- Broken English (newly-taught skeleton)
- Anime over-dramatic
- Noir detective

Stored as system prompt fragments injected into character's dialogue generation.

---

## ⚙️ TECH STACK
- **Language:** Python 3.11+
- **AI calls:** `openai` lib (works with OpenRouter, Anthropic via base_url swap)
- **Vector DB:** `chromadb` (local, free)
- **State:** JSON saves
- **CLI UI:** `rich` library for colored text, panels, prompts
- **(Optional alternate client):** another tool can call the same HTTP API on localhost.

---

## 🔐 API KEY HANDLING
- `.env` file (gitignored) holds:
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
OPENROUTER_API_KEY=...
ADMIN_PASSWORD=...

- Loaded via `python-dotenv`.
- Never hardcoded. Never logged.

---

## Roadmap rolls (director notes — phases & poll)

Treat these as stacked **feature packs**; order can slip, but Canon Engine prefers **living world → crunchy combat → economy/social depth**.

### v0.2.1 — Inventory (shipped slice)
Manual **tactical loot**: weight / encumbrance, **`/inv`**, **`/inspect`**, **`/use`** · **`/equip`**, Rare+ guarded **`/drop`**, **`/combine … and …`**, **`/give … to …`**. No combat engine yet.

### v0.2.2 — Rarity & leveling (stats)
Eight-tier rarity ladder wired end-to-end, XP from exploration/quests/discovered beats (via narrator **`state_updates`**), leveling formula (**`XP_To_Next = Level * 100`**), **`/levelup`** spend **3 stat points** per level.

### v0.2.3 — Environmental interaction — Phase 1 (pre-combat cadence)
- **Travel** — **`/travel`** moves between authored locations without menu friction.
- **Interaction** — **`/examine`**, **`/talk`** routing so NPC moods and object “secrets” can hook Luck / skill checks before combat exists.
- **Weather / time** — day/night and conditions (rain, fog) tint narration and optionally nudge DCs (**e.g. heavy storm taxing INT reads**).

### v0.2.5 — Phase 1 “feel the world exists” poll (parallel tracks)
Pick depth in any combo; all three strengthen pre-combat grounding:
| Track | Aim |
|---|---|
| **A — Travel system** | Location graph + **`/travel`**, stubs for exits/backlinks tied to lore. |
| **B — Interaction system** | **`/examine`**, **`/talk`**, mood flags on companions/NPC stubs, Luck-gated discoveries. |
| **C — Weather / time system** | World clock + weather state on session; narration + modifiers are data-driven hooks. |

### v0.3.0 → v0.3.5 — Phase 2: combat & loot
- Turn-based loop (**player beat → foe beat**) with tracked **HP / MP / stamina**.
- **Bestiary-lite** behaviours (flee scripts, resurrecting undead fluff).
- **Status effects**: Burn / Poison / Bleed scaffolding so potions earned in inventory matter.
- **Loot tables** biased by foe tier + narrator JSON with **Luck** smoothing rare drops.

### v0.4.0 → v0.4.5 — Phase 3: RPG economy & bond systems
Before starting **Phase 3**, schedule a **maintainability pass** on **`core/status.py`**, **`core/combat.py`**, and **`core/narrator_apply.py`**: split or extract helpers until each file aligns with the **≤300-line** guideline in **`.cursorrules`** (no behavior change-only mechanical moves).

| Track | Aim |
|---|---|
| **A — Economy** | Gold sinks, **`/barter`** / persuade hooks using **CHA** (no auto-resolve). |
| **B — Companion quests** | Loyalty arcs + skeletal “remember that time…” beats that unlock coop moments. |
| **C — Passive lore journal** | In-world **bestiary/lore codex UI** hydrated from **`state`** + cold archives. |

### Model routing (“RouteLLM” vibe steering)
Treat model choice as director’s chair: narrator can target **cheap daily** tiers vs **flash** tiers for exploratory prose—swap via **`NARRATOR_MODEL`** / `.env` without refactoring game logic.

### Developer warp room (**`python -m api.server --dev`**)
Bypasses UI menu narratives on the backend: **`dev_warp.json`** overlays the demo session (**see `dev_warp.example.json`**). Dev-only slashes (**`/spawn`**, **`/godmode`**) lint through the same **`POST /action`** pipe when **`CANON_ENGINE_DEV`** is active; HUD can read **`GET /health`** (**`dev_mode`**) to reveal a tucked console lane later.

---