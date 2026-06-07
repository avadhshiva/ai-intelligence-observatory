"""Unit tests for AI Intelligence Observatory."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ai_observatory.analysis import (
    ensure_story_urls,
    parse_llm_json,
    score_story,
)
from ai_observatory.collectors.news_collector import NewsCollector, _story_key
from ai_observatory.email_service import EmailService
from ai_observatory.intelligence import analyze_stories, build_briefing_payload
from ai_observatory.analysis import extract_themes


@pytest.fixture
def sample_stories():
    now = datetime.now(timezone.utc)
    return [
        {
            "title": "OpenAI launches new enterprise AI agent platform",
            "url": "https://example.com/openai-agent",
            "source": "OpenAI",
            "summary": "Enterprise deployment and governance features for AI agents.",
            "published_at": now,
            "collection_method": "rss",
        },
        {
            "title": "OpenAI launches new enterprise AI agent platform",
            "url": "https://example.com/openai-agent-duplicate",
            "source": "TechCrunch AI",
            "summary": "Duplicate headline from another source.",
            "published_at": now,
            "collection_method": "newsapi",
        },
        {
            "title": "NVIDIA unveils next-gen AI infrastructure chips",
            "url": "https://example.com/nvidia-chips",
            "source": "NVIDIA",
            "summary": "Cloud and enterprise infrastructure acceleration for LLM workloads.",
            "published_at": now,
            "collection_method": "rss",
        },
        {
            "title": "EU advances AI regulation compliance framework",
            "url": "https://example.com/eu-ai-regulation",
            "source": "Reuters AI",
            "summary": "New compliance requirements for enterprise AI systems.",
            "published_at": now,
            "collection_method": "rss",
        },
    ]


def test_story_key_deduplication():
    key1 = _story_key("OpenAI Agent Launch", "https://a.com/1")
    key2 = _story_key("openai   agent launch", "https://a.com/2")
    assert key1 == key2


def test_deduplicate_stories(sample_stories):
    deduped = NewsCollector.deduplicate(sample_stories)
    assert len(deduped) == 3


def test_score_story_range(sample_stories):
    score = score_story(sample_stories[0])
    assert 1.0 <= score <= 10.0


def test_analyze_stories_returns_top_n(sample_stories):
    result = analyze_stories(sample_stories, top_n=2)
    assert len(result) == 2
    assert result[0]["relevance_score"] >= result[1]["relevance_score"]
    assert "why_it_matters" in result[0]
    assert "enterprise_impact" in result[0]


def test_extract_themes(sample_stories):
    analyzed = analyze_stories(sample_stories, top_n=4)
    themes = extract_themes(analyzed)
    assert len(themes) >= 1
    assert any("Enterprise" in t or "Agent" in t or "Infrastructure" in t for t in themes)


def test_build_briefing_payload(sample_stories):
    analyzed = analyze_stories(sample_stories, top_n=3)
    payload = build_briefing_payload(analyzed)
    assert "stories" in payload
    assert "themes" in payload
    assert "recommended_actions" in payload
    assert len(payload["recommended_actions"]) >= 3


def test_parse_llm_json():
    raw = '```json\n{"stories": [{"title": "Test"}]}\n```'
    parsed = parse_llm_json(raw)
    assert parsed is not None
    assert parsed["stories"][0]["title"] == "Test"


def test_email_render_html(sample_stories):
    analyzed = analyze_stories(sample_stories, top_n=2)
    payload = build_briefing_payload(analyzed)
    html = EmailService.render_html(
        briefing_date=datetime.now(timezone.utc).date(),
        stories=analyzed,
        themes=payload["themes"],
        actions=payload["recommended_actions"],
        executive_summary=payload["executive_summary"],
        company_intelligence=payload.get("company_intelligence"),
        profile_name=payload.get("profile_name"),
        profile_roles=payload.get("profile_roles"),
        job_market=payload.get("job_market"),
        enterprise_adoption=payload.get("enterprise_adoption"),
        personal_cto=payload.get("personal_cto"),
    )
    assert "Executive AI Intelligence Brief" in html
    assert analyzed[0]["title"] in html
    assert analyzed[0]["url"] in html
    assert "Read source" in html
    assert "Job Market" in html or "Skills To Learn" in html


def test_save_and_retrieve_briefing(tmp_path, monkeypatch, sample_stories):
    db_path = tmp_path / "test.db"
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
    briefing_date = datetime.now(timezone.utc).date()

    briefing_id = db_module.save_briefing(
        briefing_date=briefing_date,
        subject="Test Brief",
        html_body="<html>test</html>",
        stories=analyzed,
        themes=payload["themes"],
        actions=payload["recommended_actions"],
        email_sent=False,
    )
    assert briefing_id > 0

    fetched = db_module.get_briefing_by_date(briefing_date)
    assert fetched is not None
    assert fetched["story_count"] == 2
    assert len(fetched["stories"]) == 2
