# CANON ENGINE — UI GUARDRAILS (DO NOT VIOLATE)

**Purpose:** Prevent repeated UI mistakes across iterations.

**Contract + routing:** **`canon_engine.md`** § HTTP bridge + **`api/server.py`** (`POST /action`). Canonical doc index: **`canon_engine.md` → Documentation map**. Historical Godot node names below are **layout discipline hints** for web (anchors → predictable CSS/grid, no container fights).

---

## CORE RULE

If a change reintroduces **ANY** issue listed below, STOP and revert.

---

## 1. NO CONTAINER-BASED FULL LAYOUTS

❌ **DO NOT:**

- Wrap the whole HUD in `VBoxContainer` / `HBoxContainer`
- Rely on containers for screen-wide layout

✅ **ONLY:**

- Use `Control` nodes with manual anchors for main layout

**Reason:** Containers caused overlapping UI, layout fights, and broken positioning.

---

## 2. NO OVERLAPPING ELEMENTS

❌ **NEVER** allow:

- Text overlapping buttons
- Buttons overlapping input bar
- Logs overlapping input
- Floating UI colliding with each other

✅ **ALWAYS:**

- Separate vertical layers explicitly
- Use spacing **OR** dedicated containers for small sections (like bottom deck only)

---

## 3. NO EMPTY PANELS OR PLACEHOLDERS

❌ **REMOVE:**

- Empty boxes
- Unused panels
- Debug rectangles

✅ **ONLY SHOW:**

- Real data
- Meaningful UI

---

## 4. NO DEBUG TEXT IN FINAL UI

❌ **NEVER DISPLAY:**

- `[noparse]`
- `[cmd]` unless styled intentionally
- Raw formatting tags
- Dev hints

✅ **ALWAYS:**

- Clean strings before rendering

---

## 5. CLEAR VISUAL HIERARCHY

Every screen **MUST** follow:

- **PRIMARY** (largest, brightest) → location **OR** title **OR** narration
- **SECONDARY** → player info, important context
- **TERTIARY** → system info, hints

❌ If everything looks the same → it's wrong

---

## 6. COLOR RULES (STRICT)

| Role | Color |
|------|--------|
| Health | Green |
| World / location | Teal |
| Narration | White |
| System text | Grey |
| Rewards / currency | Gold |
| Danger | Red |

❌ Do not reuse colors randomly

---

## 7. TEXT MUST ALWAYS BE READABLE

✅ **REQUIREMENTS:**

- No low-contrast text on dark background
- Proper padding from edges (20–30px)
- Autowrap enabled
- No clipping outside containers

---

## 8. INPUT BAR IS SACRED

❌ **NEVER:**

- Overlap input bar
- Move input bar randomly

✅ **ALWAYS:**

- Anchored bottom
- Full width
- Clear above it (no collisions)

---

## 9. ONE RESPONSIBILITY PER UI ELEMENT

Each element must have **ONE** purpose.

❌ **BAD:** Panel doing layout + content + decoration  

✅ **GOOD:** Label = text, bar = stat, button = action

---

## 10. DO NOT REINTRODUCE OLD SYSTEMS

❌ **DO NOT BRING BACK:**

- Minimap panel
- Tactical grid labels
- Alert bus / bio-monitor naming
- Boxed 90s UI

---

## 11. HANDBOOK RULES

✅ **MUST:**

- No raw tags (`[noparse]`, etc.)
- Proper padding
- Readable font size
- Left page must **NEVER** be empty
- Navigation must be aligned

---

## 12. BEFORE FINALIZING ANY UI CHANGE

Cursor must check:

- [ ] No overlaps
- [ ] No empty panels
- [ ] No debug text
- [ ] Text readable
- [ ] Colors follow rules
- [ ] Input bar untouched
- [ ] Layout uses anchors, not full containers

If **ANY** fail → fix before returning result

---

## FINAL RULE

If unsure:

→ **Simplify**  
→ **Remove** instead of add  
→ **Prioritize clarity over complexity**
