"""Phase 2 intelligence agent tests."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from ai_observatory.agents.career_impact import apply_career_impact
from ai_observatory.agents.company_intelligence import build_company_intelligence, tag_story_companies
from ai_observatory.agents.personal_relevance import apply_personal_relevance
from ai_observatory.agents.weekly_trends import generate_weekly_report
from ai_observatory.analysis import ensure_story_urls
from ai_observatory.database import save_briefing, save_theme_snapshots
from ai_observatory.intelligence import analyze_stories, build_briefing_payload
from ai_observatory.user_profile import UserProfile


@pytest.fixture
def sample_stories():
    now = datetime.now(timezone.utc)
    return [
        {
            "title": "OpenAI launches enterprise agent platform for TPM program delivery",
            "url": "https://example.com/openai-agent",
            "source": "OpenAI",
            "summary": "Enterprise deployment, governance, and program delivery for AI agents.",
            "published_at": now,
            "collection_method": "rss",
            "relevance_score": 8.5,
            "why_it_matters": "Important",
            "enterprise_impact": "High",
        },
        {
            "title": "AWS Bedrock adds new models for cloud AI transformation",
            "url": "https://example.com/aws-bedrock",
            "source": "AWS AI",
            "summary": "Amazon Web Services expands Bedrock for enterprise adoption.",
            "published_at": now,
            "collection_method": "rss",
            "relevance_score": 7.8,
            "why_it_matters": "Important",
            "enterprise_impact": "High",
        },
    ]


def test_ensure_story_urls_adds_fallback():
    stories = [{"title": "Missing URL story", "url": ""}]
    result = ensure_story_urls(stories)
    assert result[0]["url"].startswith("https://")
    assert result[0]["url_fallback"] is True


def test_ensure_story_urls_preserves_valid():
    stories = [{"title": "Valid", "url": "https://example.com/story"}]
    result = ensure_story_urls(stories)
    assert result[0]["url"] == "https://example.com/story"
    assert result[0]["url_fallback"] is False


def test_company_tagging(sample_stories):
    tagged = tag_story_companies(sample_stories)
    assert "OpenAI" in tagged[0]["companies"]
    assert "AWS" in tagged[1]["companies"]


def test_personal_relevance_scoring(sample_stories):
    tagged = tag_story_companies(sample_stories)
    scored = apply_personal_relevance(tagged)
    assert all(1.0 <= s["personal_relevance_score"] <= 10.0 for s in scored)
    assert "final_score" in scored[0]


def test_career_impact_by_role(sample_stories):
    tagged = tag_story_companies(sample_stories)
    enriched = apply_career_impact(tagged)
    assert "TPM" in enriched[0]["career_impact"]
    assert "AI Transformation Manager" in enriched[0]["career_impact"]
    assert enriched[0]["career_impact_summary"]


def test_build_company_intelligence(sample_stories):
    tagged = tag_story_companies(sample_stories)
    intel = build_company_intelligence(tagged)
    assert intel["companies"]["OpenAI"]["story_count"] >= 1
    assert intel["companies"]["AWS"]["story_count"] >= 1


def test_intelligence_analyze_stories(sample_stories):
    result = analyze_stories(sample_stories, top_n=2)
    assert len(result) == 2
    assert all(s.get("url") for s in result)
    assert all(s.get("career_impact") for s in result)
    assert all(s.get("personal_relevance_score") for s in result)


def test_briefing_payload_includes_company_intel(sample_stories):
    analyzed = analyze_stories(sample_stories, top_n=2)
    payload = build_briefing_payload(analyzed)
    assert "company_intelligence" in payload
    assert payload["profile_roles"]


def test_theme_snapshots_and_weekly_report(tmp_path, monkeypatch, sample_stories):
    db_path = tmp_path / "phase2.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    import ai_observatory.config as config_module
    import ai_observatory.database as db_module

    config_module.settings.database_url = f"sqlite:///{db_path}"
    db_module.engine = db_module.create_engine(config_module.settings.database_url)
    db_module.SessionLocal = db_module.sessionmaker(
        bind=db_module.engine, autoflush=False, autocommit=False
    )

    analyzed = analyze_stories(sample_stories, top_n=2)
    payload = build_briefing_payload(analyzed)
    briefing_date = date.today()

    save_briefing(
        briefing_date=briefing_date,
        subject="Test",
        html_body="<html></html>",
        stories=analyzed,
        themes=payload["themes"],
        actions=payload["recommended_actions"],
        intelligence={"company_intelligence": payload["company_intelligence"]},
    )
    save_theme_snapshots(
        briefing_date=briefing_date,
        themes=[{"theme": t, "count": 1} for t in payload["themes"]],
        categories={"Agents & Automation": 1},
        company_activity={"OpenAI": 1, "AWS": 1},
    )

    report = generate_weekly_report(briefing_date)
    assert report["briefing_count"] >= 1
    assert "rising_themes" in report
