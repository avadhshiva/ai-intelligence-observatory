"""Phase 3 intelligence tests."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from ai_observatory.agents.enterprise_adoption import (
    TRACKED_INDUSTRIES,
    build_enterprise_adoption_report,
    detect_industry,
)
from ai_observatory.agents.job_market import (
    JOB_CATEGORIES,
    build_daily_job_market_summary,
    detect_emerging_skills,
    detect_job_signals,
)
from ai_observatory.agents.personal_cto import build_personal_cto_brief
from ai_observatory.database import save_job_market_snapshot
from ai_observatory.intelligence import build_briefing_payload, build_phase3_intelligence
from ai_observatory.reports.pdf_generator import build_weekly_pdf_payload, generate_weekly_pdf


@pytest.fixture
def sample_stories():
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "title": "Bank launches AI transformation program with TPM-led delivery",
            "url": "https://example.com/bank-ai",
            "source": "Reuters AI",
            "summary": "Major bank deploys AI governance and program management for enterprise adoption.",
            "published_at": now,
            "relevance_score": 8.0,
            "final_score": 8.5,
            "why_it_matters": "Important",
            "enterprise_impact": "High",
            "companies": ["Microsoft"],
            "category": "Enterprise & Adoption",
        },
        {
            "title": "Healthcare provider scales agent automation with RAG pipeline",
            "url": "https://example.com/health-rag",
            "source": "TechCrunch AI",
            "summary": "Hospital network uses retrieval augmented generation and MLOps for clinical workflows.",
            "published_at": now,
            "relevance_score": 7.5,
            "final_score": 8.0,
            "why_it_matters": "Important",
            "enterprise_impact": "High",
            "companies": ["Google"],
            "category": "Agents & Automation",
        },
    ]


def test_job_market_category_detection(sample_stories):
    signals = detect_job_signals(sample_stories)
    assert signals.get("AI Transformation", 0) >= 1
    assert signals.get("TPM", 0) >= 1


def test_emerging_skills_detection(sample_stories):
    skills = detect_emerging_skills(sample_stories)
    skill_names = {s["skill"] for s in skills}
    assert "RAG & retrieval" in skill_names or "Agent orchestration" in skill_names


def test_daily_job_market_summary(sample_stories):
    summary = build_daily_job_market_summary(sample_stories)
    assert summary["total_stories_analyzed"] == 2
    assert "summary" in summary
    assert len(summary["emerging_skills"]) >= 1


def test_enterprise_industry_detection(sample_stories):
    assert "Banking" in detect_industry(sample_stories[0])
    assert "Healthcare" in detect_industry(sample_stories[1])


def test_enterprise_adoption_report(sample_stories):
    report = build_enterprise_adoption_report(sample_stories)
    assert report["industries"]["Banking"]["active"] is True
    assert report["industries"]["Healthcare"]["active"] is True
    assert len(report["notable_implementations"]) >= 1


def test_personal_cto_brief(sample_stories):
    cto = build_personal_cto_brief(sample_stories)
    assert cto["recommended_actions"]
    assert cto["skills_to_learn"]
    assert cto["story_insights"]
    assert cto["story_insights"][0]["why_this_matters_to_me"]


def test_phase3_intelligence_bundle(sample_stories):
    bundle = build_phase3_intelligence(sample_stories)
    assert "job_market" in bundle
    assert "enterprise_adoption" in bundle
    assert "personal_cto" in bundle


def test_briefing_payload_includes_phase3(sample_stories):
    payload = build_briefing_payload(sample_stories)
    assert payload.get("job_market")
    assert payload.get("enterprise_adoption")
    assert payload.get("personal_cto")


def test_weekly_pdf_generation(tmp_path, monkeypatch, sample_stories):
    db_path = tmp_path / "phase3.db"
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    import ai_observatory.config as config_module
    import ai_observatory.database as db_module
    import ai_observatory.reports.pdf_generator as pdf_module

    config_module.settings.database_url = f"sqlite:///{db_path}"
    db_module.engine = db_module.create_engine(config_module.settings.database_url)
    db_module.SessionLocal = db_module.sessionmaker(
        bind=db_module.engine, autoflush=False, autocommit=False
    )
    pdf_module.REPORTS_DIR = reports_dir

    payload = build_briefing_payload(sample_stories)
    briefing_date = date.today()
    db_module.save_briefing(
        briefing_date=briefing_date,
        subject="Test",
        html_body="<html></html>",
        stories=sample_stories,
        themes=["Enterprise AI adoption"],
        actions=["Review"],
        intelligence={
            "company_intelligence": payload["company_intelligence"],
            "job_market": payload["job_market"],
            "enterprise_adoption": payload["enterprise_adoption"],
            "personal_cto": payload["personal_cto"],
        },
    )
    save_job_market_snapshot(briefing_date, payload["job_market"])

    pdf_payload = build_weekly_pdf_payload(briefing_date)
    assert pdf_payload["top_stories"]
    assert pdf_payload["vendor_scorecards"]

    pdf_path = generate_weekly_pdf(briefing_date)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 500
