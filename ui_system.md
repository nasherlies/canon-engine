# CANON ENGINE — UI SYSTEM

**Status:** Retro **look reference** only. **Shipped player surface** = localhost web UI (`canon_engine.md` § HTTP bridge). **Layout authority** when editing HUD = **`ui_guardrails.md`** (+ `resolution_layout_fix_spec.md` for fixed-size targets).

Version: v0.1 · Style inspiration: 90s CRPGs (Eye of the Beholder, Wizardry, Lands of Lore) + FMV overlays

---

## CORE UI PHILOSOPHY

The UI should feel like:

- A **control panel into another world**
- Slightly **mechanical / diegetic** (like you're operating a device, not just reading text)
- Modular, panel-based, expandable
- **`python main.py`** still exposes a terminal/Rich harness that echoes this vibe; binding / JSON payloads are **`POST /action`**.

---

## SCREEN LAYOUT (BASED ON REFERENCES)

```text
+------------------------------------------------------+
| [MINIMAP]     [STATUS PANEL]     [EVENT ALERTS]      |
+-------------------+----------------------------------+
|                   |                                  |
|   WORLD VIEW      |   SIDE PANELS (STACKED)          |
|   (Narrative)     |   - Companions                   |
|                   |   - Stats                        |
|                   |   - Inventory                    |
|                   |   - System Info                  |
|                   |                                  |
+-------------------+----------------------------------+
| COMMAND INPUT + LOG FEED                            |
+------------------------------------------------------+
```

---

## UI PANELS

### 1. WORLD VIEW (CENTER)

**Purpose:** Main narrative display (AI output)

- Displays: scene descriptions, dialogue, combat narration
- Styled as: boxed panel, scrollable history
- Should support: highlighted keywords later; color-coded item rarity in text

### 2. MINIMAP (TOP LEFT)

**Purpose:** Abstract spatial awareness

Early version: text-based lines (location label + directions). Later: ASCII grid, then pixel sprites in the web shell.

### 3. STATUS PANEL (TOP CENTER)

HP / MP / stamina bars, level, buffs/debuffs, currency.

### 4. EVENT ALERTS (TOP RIGHT)

Quest updates, loot pings, companion reactions.

### 5. COMPANION PANEL (RIGHT)

Name, text portrait placeholder, loyalty, status.

### 6. INVENTORY PANEL

Scrollable list, grouped by rarity, color-coded tiers.

### 7. COMMAND INPUT + LOG (BOTTOM)

Input line + history of actions and system echoes.

---

## INTERACTION SYSTEM

- All interaction via `/commands`
- UI updates after each command from **saved session state** (never by mutating narrative directly from raw AI strings in the UI layer)
- UI must not block indefinitely without a prompt; one thread, one input line

---

## VISUAL STYLE (TERMINAL)

Use `rich`: `Panel`, `Columns`, `Layout`.  
Palette (item tiers): Dirt/Common dim white; Uncommon green; Rare blue; Epic magenta; Legendary yellow; Mythical red.  
Borders: `ROUNDED`, `HEAVY`, or `DOUBLE` as appropriate.

---

## UI STATE SYNC

UI reads from the same structures `state_manager` persists (in v0.1+, JSON saves). The layout layer only renders a `dict` (or future typed state) prepared by engine/state code — not ad-hoc AI output.

---

## UI MODES

- **NORMAL** — standard layout
- **COMBAT** — enemy emphasis + action hints (later)
- **ADMIN** — debug / raw state (later)

---

## FUTURE (GODOT LAYER)

Map panels to Control nodes; animated portraits; AI backgrounds; clickable UI.

---

## NON-NEGOTIABLE UI RULES

1. Do not wipe narrative history; only append and trim display window if needed.
2. Panels reflect state the engine last wrote.
3. No modal blocking popups; layout stays consistent across modes.
4. Panels will be collapsible later; keep density sane.

---

## TEST CASE (GARROS)

Load Garros, skeleton companion, dungeon: narrative in world view; companion panel; inventory; status bars — all from synced state.

---

## ASSETS FOLDER (FOR GODOT / ART LATER)

See `assets/README.md` for the intended tree (`assets/ui/frames`, `icons`, `backgrounds`, `portraits`, `fonts`, `audio`). Terminal v0.1 does not load these files yet; paths are reserved so structure stays stable.
