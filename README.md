# Canon Engine

Personal AI-narrated infinite RPG: **Python** engine + **localhost web UI** (browser). **Documentation index:** [canon_engine.md § Documentation map](canon_engine.md) (single routing table — use it instead of duplicating docs).

## Requirements

- Python 3.11+

## Setup

```bash
pip install -r requirements.txt
```

Secrets live only in **`.env`** at the repo root (**never** in `.py` / committed `.json`). Policy and env knobs: **`# API KEY & COST MANAGEMENT RULES.txt`**.

## Run (shipped UX)

**Easiest — double-click `Canon Engine.bat` at the repo root.** The launcher frees port **8765** if a previous run is still holding it, starts the engine, and opens your browser at **<http://127.0.0.1:8765/>**. Close the console window (or press Ctrl+C) to stop. First run: open **SETTINGS → NARRATOR · API KEYS**, paste an OpenRouter / OpenAI / Anthropic key, click SAVE — it lands in `.env` and the running engine picks it up without a restart.

Manual equivalent (one Python command, no Node, no build step):

```bash
python -m api.server
```

Then open **<http://127.0.0.1:8765/>**. Static UI lives in **`web/`** (HTML / CSS / vanilla JS modules); engine still owns rules, saves, narrator, combat (see **`canon_engine.md`** § HTTP bridge and **`api/server.py`**).

### Build a frozen API binary (optional)

For shipping **`api_server.exe`** next to a client:

```bash
pip install -r requirements-dev.txt
python tools/build_api_exe.py
```

Output layout depends on **`tools/build_api_exe.py`** / **`tools/api_server.spec`**. Runtime **`requirements.txt`** stays unchanged.

## Run (legacy harness)

Terminal + Rich menu / session:

```bash
python main.py
```

Same slash-command rules as HTTP; panels follow **`ui_system.md`** aesthetically (reference only).

## Tests

```bash
python -m pytest tests/ -p no:pytest-qt
```

**Playability (API contract):** **`tests/test_playability_smoke.py`** exercises **`GET /health`**, handbook, journal, tutorial preset boot, one **`/look`**, and required **`layout`** keys. Run before you call the HTTP surface “playable”:

```bash
python -m pytest tests/test_playability_smoke.py -q
```

That gate verifies **Python + HTTP** only. You still need a valid **`.env`** if you want full AI narration.

Details: **`CANON_ENGINE_MASTER_MANUAL.md`** § Tests; save tests avoid touching real `saves/` when patched.

## More

Design + systems: **`canon_engine.md`**. Operator glossary + §5 log: **`CANON_ENGINE_MASTER_MANUAL.md`**. HTTP bridge: **`canon_engine.md`** § HTTP bridge + **`api/server.py`**. Milestones: **`roadmap.md`**. Changelog: **`canonchanges.md`**.
