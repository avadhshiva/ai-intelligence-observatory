"""Dashboard startup validation — imports full dashboard dependency chain."""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "dashboard"))

GRAPH = [
    ("dashboard/app.py", [
        "streamlit",
        "pandas",
        "plotly.express",
        "ai_observatory.agents.company_intelligence",
        "ai_observatory.agents.weekly_trends",
        "ai_observatory.crew",
        "ai_observatory.crew_metrics",
        "ai_observatory.database",
        "ai_observatory.reports.pdf_generator",
        "ai_observatory.user_profile",
    ]),
    ("ai_observatory.crew", [
        "crewai",
        "ai_observatory.collectors.news_collector",
        "ai_observatory.crew_parser",
        "ai_observatory.intelligence",
    ]),
    ("ai_observatory.collectors.news_collector", [
        "feedparser",
        "httpx",
    ]),
    ("ai_observatory.reports.pdf_generator", [
        "reportlab.lib.pagesizes",
    ]),
    ("ai_observatory.database", [
        "sqlalchemy",
    ]),
]

errors: list[tuple[str, str, str]] = []

for parent, deps in GRAPH:
    for dep in deps:
        try:
            __import__(dep)
            print(f"OK  {parent} -> {dep}")
        except Exception as exc:
            tb = traceback.format_exc()
            errors.append((parent, dep, f"{exc}\n{tb}"))
            print(f"FAIL {parent} -> {dep}: {exc}")

# Validate crew entrypoint
try:
    from ai_observatory.crew import run_observatory_crew

    assert callable(run_observatory_crew)
    print("OK  run_observatory_crew callable")
except Exception as exc:
    errors.append(("crew", "run_observatory_crew", str(exc)))
    print(f"FAIL run_observatory_crew: {exc}")

# Deterministic fallback path
try:
    from ai_observatory.crew import _run_deterministic_pipeline
    from ai_observatory.collectors.news_collector import NewsCollector

    stories = NewsCollector().collect_rss()[:3]
    if stories:
        result = _run_deterministic_pipeline(stories, send_email=False)
        assert result.get("success"), result
        print(f"OK  deterministic fallback ({result.get('story_count')} stories)")
    else:
        print("SKIP deterministic fallback (no RSS stories)")
except Exception as exc:
    tb = traceback.format_exc()
    errors.append(("crew", "deterministic_fallback", f"{exc}\n{tb}"))
    print(f"FAIL deterministic fallback: {exc}")

print(f"\nStartup validation errors: {len(errors)}")
sys.exit(1 if errors else 0)
