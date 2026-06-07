"""Validate dashboard import chain without executing Streamlit UI."""
from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

IMPORTS = [
    "pandas",
    "plotly.express",
    "streamlit",
    "ai_observatory.agents.company_intelligence",
    "ai_observatory.crew_metrics",
    "ai_observatory.database",
    "ai_observatory.user_profile",
]

errors: list[str] = []
for mod in IMPORTS:
    try:
        importlib.import_module(mod)
        print(f"OK  dashboard chain -> {mod}")
    except Exception as exc:
        errors.append(f"{mod}: {exc}")
        print(f"FAIL dashboard chain -> {mod}: {exc}")

app_path = ROOT / "dashboard" / "app.py"
ast.parse(app_path.read_text(encoding="utf-8"))
print(f"OK  {app_path.name} syntax valid")

compile(app_path.read_text(encoding="utf-8"), str(app_path), "exec")
print(f"OK  {app_path.name} compile valid")

sys.exit(1 if errors else 0)
