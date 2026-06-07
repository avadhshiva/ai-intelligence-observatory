"""Tests for CrewAI output parsing and JSON repair."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ai_observatory.crew_parser import (
    RAW_OUTPUT_PATH,
    parse_crew_output,
    parse_json_with_repair,
    repair_json_text,
    validate_briefing_data,
)
from ai_observatory.schemas.crew_output import CrewBriefingSchema


VALID_BRIEFING = {
    "stories": [
        {
            "title": "OpenAI launches enterprise platform",
            "url": "https://example.com/1",
            "source": "OpenAI",
            "relevance_score": 8.5,
            "why_it_matters": "Important for enterprise AI.",
            "enterprise_impact": "High impact.",
            "summary": "Launch details.",
        }
    ],
    "executive_summary": "Key AI news today.",
    "themes": ["Enterprise AI adoption"],
    "recommended_actions": ["Review vendor roadmap"],
}


def test_repair_markdown_fences():
    raw = '```json\n{"stories": [{"title": "Test", "url": "https://a.com"}]}\n```'
    repaired, steps = repair_json_text(raw)
    assert "stripped_markdown_fences" in steps
    data, repair_steps, err = parse_json_with_repair(raw)
    assert data is not None
    assert err is None


def test_repair_trailing_commas():
    raw = '{"stories": [{"title": "Test", "url": "https://a.com",}], "themes": [],}'
    data, steps, err = parse_json_with_repair(raw)
    assert data is not None
    assert "removed_trailing_commas" in steps or "json_repair_library" in steps


def test_repair_escaped_newlines():
    raw = '{"stories": [{"title": "Line one\\nLine two", "url": "https://a.com"}]}'
    data, steps, err = parse_json_with_repair(raw)
    assert data is not None


def test_pydantic_validation_success():
    validated, err = validate_briefing_data(VALID_BRIEFING)
    assert validated is not None
    assert err is None
    assert isinstance(validated, CrewBriefingSchema)


def test_pydantic_validation_failure():
    validated, err = validate_briefing_data({"stories": []})
    assert validated is None
    assert err is not None


def test_parse_crew_output_success(tmp_path, monkeypatch):
    monkeypatch.setattr("ai_observatory.crew_parser.RAW_OUTPUT_PATH", tmp_path / "raw.json")
    monkeypatch.setattr("ai_observatory.crew_parser.LOGS_DIR", tmp_path)

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    import ai_observatory.config as config_module
    import ai_observatory.database as db_module

    config_module.settings.database_url = f"sqlite:///{db_path}"
    db_module.engine = db_module.create_engine(config_module.settings.database_url)
    db_module.SessionLocal = db_module.sessionmaker(
        bind=db_module.engine, autoflush=False, autocommit=False
    )
    db_module.init_db()

    mock_result = MagicMock()
    mock_result.raw = json.dumps(VALID_BRIEFING)
    mock_result.json_dict = None
    mock_result.token_usage = MagicMock()
    mock_result.token_usage.model_dump.return_value = {"total_tokens": 1200}

    result = parse_crew_output(mock_result, execution_time_ms=1500.0)
    assert result.success is True
    assert result.used_fallback is False
    assert result.validated_data is not None
    assert (tmp_path / "raw.json").exists()


def test_parse_crew_output_fallback_on_invalid(tmp_path, monkeypatch):
    monkeypatch.setattr("ai_observatory.crew_parser.RAW_OUTPUT_PATH", tmp_path / "raw.json")
    monkeypatch.setattr("ai_observatory.crew_parser.LOGS_DIR", tmp_path)

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    import ai_observatory.config as config_module
    import ai_observatory.database as db_module

    config_module.settings.database_url = f"sqlite:///{db_path}"
    db_module.engine = db_module.create_engine(config_module.settings.database_url)
    db_module.SessionLocal = db_module.sessionmaker(
        bind=db_module.engine, autoflush=False, autocommit=False
    )
    db_module.init_db()

    mock_result = MagicMock()
    mock_result.raw = "This is not JSON at all"
    mock_result.json_dict = None
    mock_result.token_usage = MagicMock()
    mock_result.token_usage.model_dump.return_value = {"total_tokens": 0}

    result = parse_crew_output(mock_result, execution_time_ms=800.0)
    assert result.success is False
    assert result.used_fallback is True
    assert result.parse_error is not None


def test_crew_diagnostics_summary(tmp_path, monkeypatch):
    db_path = tmp_path / "metrics.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    import ai_observatory.config as config_module
    import ai_observatory.database as db_module
    from ai_observatory.crew_metrics import get_crew_diagnostics_summary, record_crew_parse_run

    config_module.settings.database_url = f"sqlite:///{db_path}"
    db_module.engine = db_module.create_engine(config_module.settings.database_url)
    db_module.SessionLocal = db_module.sessionmaker(
        bind=db_module.engine, autoflush=False, autocommit=False
    )
    db_module.init_db()

    record_crew_parse_run("success", False, None, 1000, {"total_tokens": 500}, [], "preview")
    record_crew_parse_run("failed", True, "bad json", 900, {"total_tokens": 100}, [], "preview")

    summary = get_crew_diagnostics_summary()
    assert summary["total_runs"] == 2
    assert summary["fallback_rate"] == 50.0
