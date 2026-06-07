#!/usr/bin/env python3
"""Startup health check — validates imports, DB, CrewAI, config, and filesystem."""

from __future__ import annotations

import importlib
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

REQUIRED_TABLES = [
    "briefings",
    "theme_snapshots",
    "weekly_reports",
    "job_market_snapshots",
    "enterprise_adoption_snapshots",
    "weekly_pdf_reports",
    "stories",
    "crew_parse_runs",
    "raw_crew_outputs",
]

REQUIRED_DIRS = ["data", "logs", "config", "dashboard", "src", "tests"]

IMPORT_MODULES = [
    "ai_observatory.config",
    "ai_observatory.logging_setup",
    "ai_observatory.database",
    "ai_observatory.collectors.news_collector",
    "ai_observatory.crew",
    "ai_observatory.crew_parser",
    "ai_observatory.crew_metrics",
    "ai_observatory.email_service",
    "ai_observatory.reports.pdf_generator",
    "ai_observatory.schemas.crew_output",
    "feedparser",
    "httpx",
    "jinja2",
    "json_repair",
    "pydantic",
    "sqlalchemy",
]

DASHBOARD_IMPORT_MODULES = [
    "pandas",
    "plotly.express",
    "streamlit",
    "ai_observatory.agents.company_intelligence",
    "ai_observatory.crew_metrics",
    "ai_observatory.database",
    "ai_observatory.user_profile",
]


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    warnings: list[str] = field(default_factory=list)


def check_imports() -> CheckResult:
    failures: list[str] = []
    for mod in IMPORT_MODULES:
        try:
            importlib.import_module(mod)
        except Exception as exc:
            failures.append(f"{mod}: {exc}")
    if failures:
        return CheckResult("imports", False, "; ".join(failures))
    return CheckResult("imports", True, f"{len(IMPORT_MODULES)} modules resolved")


def check_database() -> CheckResult:
    try:
        from sqlalchemy import inspect, text

        import ai_observatory.database as db

        db.init_db()
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        missing = [t for t in REQUIRED_TABLES if t not in tables]
        if missing:
            return CheckResult("database", False, f"Missing tables: {', '.join(missing)}")
        return CheckResult("database", True, f"Connected — {len(tables)} tables")
    except Exception as exc:
        return CheckResult("database", False, str(exc))


def check_required_folders() -> CheckResult:
    missing = [name for name in REQUIRED_DIRS if not (ROOT / name).exists()]
    if missing:
        return CheckResult("required_folders", False, f"Missing: {', '.join(missing)}")

    from ai_observatory.config import PROJECT_ROOT
    from ai_observatory.crew_parser import LOGS_DIR

    writable = True
    for path in (PROJECT_ROOT / "data", LOGS_DIR):
        path.mkdir(exist_ok=True)
        try:
            probe = path / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError:
            writable = False
    if not writable:
        return CheckResult("required_folders", False, "data/ or logs/ not writable")
    return CheckResult("required_folders", True, f"{len(REQUIRED_DIRS)} folders present, writable OK")


def check_crewai() -> CheckResult:
    try:
        from ai_observatory.crew import _crewai_types, run_observatory_crew

        if not callable(run_observatory_crew):
            return CheckResult("crewai", False, "run_observatory_crew not callable")
        Agent, Crew, LLM, Process, Task = _crewai_types()
        for symbol in (Agent, Crew, LLM, Process, Task):
            if symbol is None:
                return CheckResult("crewai", False, "CrewAI symbol import returned None")
        return CheckResult("crewai", True, "CrewAI lazy import OK")
    except Exception as exc:
        return CheckResult("crewai", False, str(exc))


def check_openai_config() -> CheckResult:
    from ai_observatory.config import settings

    warnings: list[str] = []
    if not settings.openai_api_key:
        warnings.append("OPENAI_API_KEY not set — deterministic fallback will be used")
    if not settings.use_llm:
        warnings.append("USE_LLM=false — CrewAI pipeline disabled")
    detail = f"model={settings.openai_model}, use_llm={settings.use_llm}, key_configured={bool(settings.openai_api_key)}"
    return CheckResult("openai_config", True, detail, warnings)


def check_smtp_config() -> CheckResult:
    from ai_observatory.config import settings

    warnings: list[str] = []
    configured = all([settings.smtp_host, settings.smtp_user, settings.smtp_password, settings.email_from])
    if not configured:
        warnings.append("SMTP credentials incomplete — email delivery disabled")
    if not settings.email_recipients:
        warnings.append("EMAIL_RECIPIENTS empty — no recipients configured")
    detail = (
        f"host={settings.smtp_host}, port={settings.smtp_port}, "
        f"smtp_ready={configured}, recipients={len(settings.email_recipients)}"
    )
    return CheckResult("smtp_config", True, detail, warnings)


def check_newsapi_config() -> CheckResult:
    from ai_observatory.config import settings

    warnings: list[str] = []
    if not settings.newsapi_key:
        warnings.append("NEWSAPI_KEY not set — RSS-only collection")
    detail = f"key_configured={bool(settings.newsapi_key)}, query={settings.newsapi_query[:40]}..."
    return CheckResult("newsapi_config", True, detail, warnings)


def check_streamlit_dashboard_imports() -> CheckResult:
    import ast

    failures: list[str] = []
    for mod in DASHBOARD_IMPORT_MODULES:
        try:
            importlib.import_module(mod)
        except Exception as exc:
            failures.append(f"{mod}: {exc}")

    app_path = ROOT / "dashboard" / "app.py"
    source = app_path.read_text(encoding="utf-8")
    try:
        ast.parse(source)
        compile(source, str(app_path), "exec")
    except Exception as exc:
        failures.append(f"dashboard/app.py: {exc}")

    if "use_container_width" in source:
        failures.append("dashboard/app.py: deprecated use_container_width present")
    if failures:
        return CheckResult("streamlit_dashboard", False, "; ".join(failures))
    return CheckResult("streamlit_dashboard", True, "dashboard import chain OK")


def run_all_checks() -> tuple[list[CheckResult], bool]:
    checks = [
        check_imports(),
        check_database(),
        check_required_folders(),
        check_crewai(),
        check_openai_config(),
        check_smtp_config(),
        check_newsapi_config(),
        check_streamlit_dashboard_imports(),
    ]
    ok = all(c.ok for c in checks)
    return checks, ok


def main() -> int:
    print("AI Intelligence Observatory — Health Check")
    print("=" * 50)
    checks, all_ok = run_all_checks()
    for result in checks:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")
        for warning in result.warnings:
            print(f"       WARN: {warning}")
    print("=" * 50)
    if all_ok:
        print("Overall: HEALTHY")
        return 0
    print("Overall: UNHEALTHY")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
