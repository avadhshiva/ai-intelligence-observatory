"""Import audit script — validates all project modules resolve."""
from __future__ import annotations

import ast
import importlib
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

MODULES = [
    "ai_observatory.config",
    "ai_observatory.logging_setup",
    "ai_observatory.diagnostics",
    "ai_observatory.database",
    "ai_observatory.analysis",
    "ai_observatory.sources",
    "ai_observatory.collectors.news_collector",
    "ai_observatory.crew_parser",
    "ai_observatory.crew_metrics",
    "ai_observatory.crew",
    "ai_observatory.intelligence",
    "ai_observatory.pipeline",
    "ai_observatory.email_service",
    "ai_observatory.scheduler",
    "ai_observatory.user_profile",
    "ai_observatory.schemas.crew_output",
    "ai_observatory.agents.personal_relevance",
    "ai_observatory.agents.company_intelligence",
    "ai_observatory.agents.career_impact",
    "ai_observatory.agents.weekly_trends",
    "ai_observatory.agents.job_market",
    "ai_observatory.agents.personal_cto",
    "ai_observatory.agents.enterprise_adoption",
    "ai_observatory.reports.pdf_generator",
    "ai_observatory.__main__",
]

errors: list[str] = []
for mod in MODULES:
    try:
        importlib.import_module(mod)
        print(f"OK  {mod}")
    except Exception as exc:
        tb = traceback.format_exc()
        errors.append(f"FAIL {mod}: {exc}\n{tb}")
        print(f"FAIL {mod}: {exc}")

# Dashboard import chain (without running streamlit)
sys.path.insert(0, str(ROOT / "dashboard"))
try:
    import importlib.util

    spec = importlib.util.spec_from_file_location("dashboard_app", ROOT / "dashboard" / "app.py")
    assert spec and spec.loader
    # Load module but skip streamlit runtime — validate imports only via ast
    source = (ROOT / "dashboard" / "app.py").read_text(encoding="utf-8")
    ast.parse(source)
    print("OK  dashboard/app.py (syntax + parse)")
except Exception as exc:
    errors.append(f"FAIL dashboard/app.py: {exc}")
    print(f"FAIL dashboard/app.py: {exc}")

print(f"\nTotal errors: {len(errors)}")
sys.exit(1 if errors else 0)
