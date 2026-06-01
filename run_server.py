#!/usr/bin/env python3
"""Start Canon Engine server in dev mode (no password required)."""
import os
import sys
from pathlib import Path

# Clear inherited ADMIN_PASSWORD for dev mode
os.environ.pop("ADMIN_PASSWORD", None)

# Load .env file
env_path = Path("/opt/data/.env")
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

# Set Canon Engine env vars
os.environ["CANON_LLM_PROVIDER"] = "openrouter"
os.environ["CANON_LLM_MODEL"] = "google/gemini-2.0-flash-001"

# Start server
os.chdir(str(Path.home() / "canon-engine"))
venv_python = str(Path.home() / "canon-engine/.venv/bin/python3")
sys.argv = [venv_python, "-m", "uvicorn", "canon_engine.api.server:app", "--host", "0.0.0.0", "--port", "8787"]
sys.executable = venv_python
os.execv(venv_python, sys.argv)
