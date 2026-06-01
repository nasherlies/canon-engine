# Canon Engine Full Rebuild Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Rebuild the complete Canon Engine game backend from the canonchanges.md spec, wiring everything into the existing web UI.

**Architecture:** Python game engine (FastAPI) with single-file web client. Core modules in `canon_engine/core/`, session handling in `canon_engine/ui/`, API in `canon_engine/api/`. The AI narrator is the heart — Python validates and applies state changes, the model narrates.

**Tech Stack:** Python 3.13, FastAPI, Uvicorn, OpenAI SDK (via OpenRouter), JSON saves

**Key Rule:** "Model proposes, engine disposes" — narrator returns JSON with state_updates, Python validates and applies.

---

## System 1: Core Framework
**Batch 1 (parallel):**

### Task 1: Command Parser (`canon_engine/core/command_parser.py`)
- Parse all slash commands: /say, /do, /think, /look, /inv, /inventory, /attack, /block, /item, /flee, /save, /load, /quicksave, /help, /menu, /quit, /start_character, /turn, /use, /equip, /drop, /combine, /give, /inspect, /stats, /addstat, /levelup, /skills, /unlock, /factions, /reputation, /craft, /shop, /buy, /sell, /barter, /rent, /scavenge, /nap, /sleep, /travel, /scout, /stealth, /cover, /climb, /interact, /map, /world, /lore, /quests, /quest, /accept, /abandon, /turnin, /npcs, /npc, /gift, /threaten, /recruit, /dismiss, /companion, /order, /soul, /remember, /anchor, /bribe, /lockpick, /gamble, /admin, /retcon, /collide, /encounter, /fight, /talk, /choices, /consequences, /summary, /author
- Bare text (no /) → /say
- Returns (kind, args_dict)
- Tests: test_command_parser.py

### Task 2: State Manager (`canon_engine/core/state_manager.py`)
- save_game(state, path) — atomic write (tmp + os.replace)
- load_game(path) — JSON parse, validation, merge defaults for missing keys
- _merge_legacy_save_shape(state) — backwards compat
- save_version: 1 on every write
- Tests: test_state_manager.py

### Task 3: Stats Module (`canon_engine/core/stats.py`)
- STAT_KEYS = STR, DEX, INT, CHA, CON, LCK
- CON/LCK table modifiers
- calculate_max_hp(player) = 50 + CON×5
- nap_heal_amount, sleep_heal_amount
- get_stat_modifier(val) = (val - 10) // 2
- Tests: test_stats.py

### Task 4: Rarity (`canon_engine/core/rarity.py`)
- 8 tiers: dirt, common, uncommon, power, rare, epic, mythical, god
- roll_rarity(rng, luck_mod=0)
- RARITY_TABLE with rank, hex color, drop weight
- Tests: test_rarity.py

### Task 5: Damage Types (`canon_engine/core/damage_types.py`)
- DAMAGE_TYPES list, normalize_damage_type, get_element_label
- Tests: inline in test_elements.py

---

## System 2: World & Memory
**Batch 2 (parallel):**

### Task 6: World (`canon_engine/core/world.py`)
- ensure_world(state) — defaults for location, weather, clock, npcs, quests, map, etc.
- advance_world_time / apply_time_passed
- weather system (every ~180 min)
- clock: minutes_total, HH:MM, day line
- travel_edges
- Tests: test_world.py

### Task 7: Memory Warm (`canon_engine/core/memory_warm.py`)
- Rolling text summary every N turns
- build_memory_summary_prompt, apply_memory_update
- Tests: test_memory.py

### Task 8: Recovery (`canon_engine/core/recovery.py`)
- /nap — 1-3h, ~15% HP heal
- /sleep — +480 min, full vitals, location_restable required
- Tests: test_recovery.py

### Task 9: Travel (`canon_engine/core/travel.py`)
- apply_engine_travel(state, destination, rng)
- Minute budget by tier (short/regional/continental)
- Weather churn on long crossings
- Tests: test_travel.py

---

## System 3: Inventory & Leveling
**Batch 3 (parallel):**

### Task 10: Inventory (`canon_engine/core/inventory.py`)
- 17-slot EQUIP_SLOTS (head, face, neck, back, chest_armor, chest_clothing, hands, waist, legs_armor, legs_clothing, feet, ring_left, ring_right, weapon_main, weapon_off, accessory_1, accessory_2)
- normalize_item(raw) — id, effects, tags, qty, weight
- carry cap: 30 + STR×2
- use_item, equip_item, drop_item, combine_items, give_item
- format_inventory_sheet
- ensure_equipment(state) — migrate legacy slots
- resolve_equip_slot(token, eq) — alias resolver
- Tests: test_inventory.py

### Task 11: Leveling (`canon_engine/core/leveling.py`)
- XP_FLOOR_PER_TURN = 5 (on /do, /say)
- add_xp, apply_level_up (+3 stat_points)
- format_levelup_display
- Tests: test_leveling.py

### Task 12: Starting Kits (`canon_engine/core/starting_kits.py`)
- Load from content/presets/starting_kits.json
- apply_starting_kit(state, preset_id)
- Tests: test_starting_kits.py

### Task 13: Item Lore (`canon_engine/core/item_lore.py`)
- Optional rarity card text on inspect
- Tests: inline

### Task 14: Equip Suggest (`canon_engine/core/equip_suggest.py`)
- After equip, hint if higher-rarity piece exists in pack
- Tests: test_equip_suggest.py

---

## System 4: Narrator AI
**Batch 4 (parallel):**

### Task 15: Narrator (`canon_engine/core/narrator.py`)
- OpenAI SDK via OpenRouter
- JSON-object responses with: narration, check, state_updates, suggested_actions, xp_add, discovered_lore, quest_update, saga_advance
- System prompt: world bible + memory + saga + quests + last 5 log lines
- Rate limit: NARRATOR_MIN_INTERVAL_SECONDS
- _JSON_INSTRUCTION — teaches model the JSON contract
- _INTRO_INSTRUCTION — opening scene
- _THINK_INSTRUCTION — internal monologue
- _fallback_intro for offline
- Tests: test_narrator.py

### Task 16: Narrator Apply (`canon_engine/core/narrator_apply.py`)
- apply_narrator_result(state, result, turn)
- Apply: narration, check, state_updates (inventory, flags, stat deltas), xp_add
- Route through: discovered_lore, quest_update, saga_advance
- normalize inventory + sync_carry after
- Tests: test_narrator_apply.py

### Task 17: Character Session (`canon_engine/core/character_session.py`)
- build_character_session_state(character) — fresh session from payload
- ensure_tutorial_state, ensure_world, seed_initial_codex
- apply_starting_kit, recalculate_stats
- pin hp = hp_max on creation
- Tests: test_character_session.py

### Task 18: Backstory (`canon_engine/core/backstory.py`)
- POST /backstory — AI-generated short backstory
- Tests: inline

### Task 19: Speech Styles (`canon_engine/core/speech_styles.py`)
- Load from content/languages/*.json
- get_speech_style_prompt(style)
- Tests: inline

---

## System 5: Status & Combat
**Batch 5 (parallel):**

### Task 20: Status Effects (`canon_engine/core/status.py`)
- STATUS_REGISTRY: fatigue, poison, bleed, stun, weaken, guard, covered, high_ground, well_rested, sheltered, dying, wounded
- apply/remove/clear_statuses_by_trigger
- tick_statuses, get_active_modifiers
- Tests: test_status.py

### Task 21: Combat Math (`canon_engine/core/combat_math.py`)
- d20 roll, AC calc, damage roll helpers
- render_hp_bar
- Tests: inline

### Task 22: Enemy AI (`canon_engine/core/enemy_ai.py`)
- Intent bands (self low HP / player low HP / default)
- Per-type abilities with cooldowns
- resolve_enemy_turn
- Tests: inline in test_combat.py

### Task 23: Elements (`canon_engine/core/elements.py`)
- Resistances, split physical/elemental mitigation
- Weather synergy (soaked + lightning, frost in wet)
- calculate_elemental_damage
- Tests: test_elements.py

### Task 24: Encounter Bridge (`canon_engine/core/encounter_bridge.py`)
- pending_encounter + encounter_data
- CHA talk bands, DEX flee contest
- transition_to_combat
- Tests: test_encounter_bridge.py

### Task 25: Combat (`canon_engine/core/combat.py`)
- start_combat / end_combat
- /attack (with index targeting), /block, /item, /flee
- Multi-enemy (up to 3), enemy auto-numbering
- Loot/XP on victory
- Combat shell gate (only /attack /block /item /flee during combat)
- D&D 2014 rules: initiative, attack rolls vs AC, natural 20/1, damage dice
- Round tracking, move announcements
- Tests: test_combat.py, test_multi_enemy.py

---

## System 6: Party & Terrain
**Batch 6 (parallel):**

### Task 26: Companions (update existing `canon_engine/systems/companions.py`)
- Wire into game session: /recruit, /dismiss, /companion, /order
- Loyalty obedience rolls
- Tests: test_companions.py

### Task 27: Party Combat (`canon_engine/core/party.py`)
- Build combat party from companions
- /order queue (attack/block/item/flee)
- Party phase after player attack
- Combo damage when companion strikes same foe
- Sync vitals back after combat
- Tests: test_party_combat.py

### Task 28: Terrain (`canon_engine/core/terrain.py`)
- get_terrain_modifiers, terrain hazards
- Cover (+2 AC), high ground (+2 ATK)
- Narrow passage cap, oil barrel, chandelier
- Tests: test_terrain.py

### Task 29: Stealth (`canon_engine/core/stealth.py`)
- /scout, /stealth, /detect, /disarm
- travel_trap_hook
- Tests: test_stealth.py

---

## System 7: Economy & NPCs
**Batch 7 (parallel):**

### Task 30: NPC System (`canon_engine/core/npc.py`)
- ensure_npcs, get_npc, get_npcs_in_location
- apply_relationship_delta (±100)
- record_npc_memory_event
- shop_price_multiplier
- Tests: test_npc.py

### Task 31: Economy (`canon_engine/core/economy.py`)
- Wallet (gold, gold_spent)
- Victory gold + monster parts
- /scavenge (LCK vs DC)
- Merchant stock, buy/sell prices
- /barter (CHA DC 12), /rent (inn)
- Tests: test_economy.py

### Task 32: Factions (`canon_engine/core/factions.py`)
- Reputation events, tiers
- Shop modifier, nemesis encounter flag
- Tests: test_factions.py

### Task 33: World Generation (`canon_engine/core/worldgen.py`)
- Seeded procedural map
- Travel edges, lore deck
- apply_procedural_world
- Tests: test_worldgen.py

---

## System 8: Progression & Depth
**Batch 8 (parallel):**

### Task 34: Crafting (`canon_engine/core/crafting.py`)
- Recipes, DC rolls, quality tiers
- /craft list, /craft <id>
- Tests: test_crafting.py

### Task 35: Skill Trees (`canon_engine/core/skills.py`)
- 4 trees, /skills, /unlock, /use
- Cleave, backstab, analyze, amplify, etc.
- Tests: test_skills.py

### Task 36: Boss Encounters (`canon_engine/core/boss.py`)
- Phase thresholds, boss abilities, death loot
- Tests: test_boss.py

### Task 37: Death & Rebirth
- `core/death.py` — death save, trigger_death, after_hp_zero
- `core/underworld.py` — soul system, enter/exit
- `core/rebirth.py` — standard/ascension/descension paths
- Tests: test_death.py, test_underworld.py, test_rebirth.py

---

## System 9: Narrative Systems
**Batch 9 (parallel):**

### Task 38: Quests (`core/quests.py`)
- Procedural quest generation from templates
- /accept, /abandon, /turnin
- Progress tracking, rewards
- Tests: test_quests.py

### Task 39: Narrator Quests (`core/narrator_quests.py`)
- Free-text quests from narrator JSON
- quest_update / quest_update_many
- Quest ↔ Codex link
- Tests: test_narrator_quests.py

### Task 40: Lore Codex (`core/lore_codex.py`)
- Discoverable cards (character/location/faction/item/history)
- Seed lore per genre
- discovered_lore from narrator
- Tests: test_lore_codex.py

### Task 41: Saga Framework (`core/saga.py`)
- Spine vs pods, macro-loop
- saga_advance / saga_hint
- Tests: test_saga.py

---

## System 10: Polish
**Batch 10 (parallel):**

### Task 42: Minigames (`core/minigames.py`)
- Lockpick + gamble logic
- Tests: test_minigames.py

### Task 43: Journal (`core/journal.py`)
- Narrative journal with chapter markers
- Tests: test_journal.py

### Task 44: Tutorial (`core/tutorial.py`)
- Step machine, practice dummy
- Tests: test_tutorial.py

### Task 45: Action Suggestions (`core/action_suggestions.py`)
- Narrator-driven action chips
- Tests: test_action_suggestions.py

### Task 46: Handbook (`core/handbook.py`)
- Merge canonchanges.md + topics.json
- Tests: test_handbook.py

### Task 47: Admin & Dev (`core/admin.py`, `core/dev_mode.py`)
- /admin, /retcon, /godmode, /spawn
- Tests: inline

---

## System 11: Server & Session Wiring
**Batch 11:**

### Task 48: Game Session (`canon_engine/ui/game_session.py`)
- step_session_turn(state, command, rng, character=None)
- Dispatch to all handlers
- Combat shell gate
- Idle clock skip for utility commands
- Autosave
- Tests: test_game_session.py

### Task 49: Server Update (`canon_engine/api/server.py`)
- Wire all new modules into FastAPI endpoints
- layout_payload with all HUD blocks
- New endpoints: /journal, /codex, /quests, /manual, /equipment/slots, /me, /settings/keys
- Tests: test_api_server.py

---

## System 12: Content Files
**Batch 12:**

### Task 50: Content JSONs
- content/presets/characters.json (9 heroes)
- content/enemies.json (bestiary)
- content/merchants.json
- content/recipes.json, content/craft_catalog.json
- content/skills_trees.json
- content/bosses.json
- content/factions.json
- content/terrain_features.json
- content/traps.json
- content/monster_parts.json
- content/quest_templates.json
- content/npcs_seed_templates.json
- content/worldgen_tables.json
- content/item_lore.json
- content/lore/seed_lore.json
- content/narrative/saga_seed.json, pod_quests.json
- content/settings_catalog.json
- content/starting_locations.json
- content/languages/*.json (speech styles)
- content/handbook/topics.json
- content/tutorial/tutorial_steps.json
- content/manual/manual.json

---

## System 13: Web UI Enhancements
**Batch 13:**

### Task 51: Combat HUD Panel
- HP bars, enemy roster, action buttons (ATTACK/BLOCK/ITEM/LOOK/ORDER/FLEE)
- Auto-numbered enemies, round tracking

### Task 52: Overlay Improvements
- Inventory: per-row USE/EQUIP/INSPECT/COMBINE/DROP
- Stats: stat bars with +, skill tree, lore tab
- Equipment: 17-slot body map SVG

### Task 53: New Overlays
- Quest Log: ACTIVE/COMPLETED/FAILED with objectives
- Codex: tabbed modal with discovered cards
- Player Manual: topic reader
- Journal: narrative journal view

### Task 54: HUD Polish
- Save manager improvements
- Settings panel with API key input
- Tutorial walkthrough
- Action suggestion chips
