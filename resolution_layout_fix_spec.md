# CANON ENGINE — RESOLUTION + LAYOUT FIX SPEC

Version: v0.1.2-layout

Priority: Fixed window sizing, reduced HUD scrollbars, panel breathing room, Settings chrome.

**Note:** The live game may use **`cinematic_hud_layout.gd`** (anchor-only deck). Numbers below targeted an **HSplit + column** HUD; treat them as **soft reference** unless that layout is restored.

---

## RESOLUTION

- **Project Settings:** viewport **1280×720**, stretch **canvas_items**, aspect **expand**, optional window width/height override **1280×720**.
- **Boot + GameHUD:** `DisplayServer.window_set_size` and `window_set_min_size` to **1280×720** so editor/run scene fill the frame without letterboxed “inner box”.

---

## HUD LAYOUT (targets)

- **Top row** (MINIMAP | STATUS | EVENTS): **~80px** tall; **no** TEXTURE stamp lines; compact text; **no** RichText scrollbars (`scroll_active = false`, `clip_contents = true`).
- **Mid band:** **HSplit** at **~780px**, mid band height **~452px** (fits chrome + margins inside 720px window).
- **Right column** width **480px**; panels **Companions / Inventory / System** min heights **140 / 160 / 80**; extra slack expands at bottom of column.
- **World View:** only scrollable narrative region as needed (`TextEdit`).
- **Command log** inner height target **~56px** (plus panel header chrome).
- **Command row** **36px** with **`>`** prompt.

---

## DATA TRUNCATION (no fake scroll)

- **Events:** single line, truncated.
- **Minimap:** up to **2** detail lines, capped length.
- **Status:** compact **3-line** numeric summary (no wide meter bars).
- **Companions:** max **3**, then `…+N more`.
- **Inventory BBCode:** max **5** rows, then `…+N more`.
- **System:** one line, clip.

---

## MAIN MENU

- **LINK** chip margin **8px** from top-left; footer **8px** from bottom; title pushed with top spacer (~188px) for vertical balance.

---

## SETTINGS

- Same **menu_ambient** backdrop + **Press Start 2P** + palette via **`main_menu_ui.gd`**.
- Form wrapped in **metallic StyleBoxTexture** panel; fields use dark fill + amber focus border.
- **Save & Back** / **Back (discard)** use START / QUIT accent buttons.

---

## RULES

- No Python backend changes for this milestone.
- Test at **1280×720** only.

---

_End — implementation lives under `godot/` (e.g. `project.godot`, `game_hud_layout.gd`, `cinematic_hud_layout.gd`, `main_layout_sync.gd`, `ui_settings_screen.gd`)._
