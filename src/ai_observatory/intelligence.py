"""Phase 2/3 intelligence orchestration — deterministic agent pipeline."""

from __future__ import annotations

from datetime import date
from typing import Any

from ai_observatory.agents.career_impact import apply_career_impact
from ai_observatory.agents.company_intelligence import (
    build_company_intelligence,
    tag_story_companies,
)
from ai_observatory.agents.enterprise_adoption import (
    build_enterprise_adoption_report,
    tag_stories_with_industries,
)
from ai_observatory.agents.job_market import build_daily_job_market_summary
from ai_observatory.agents.personal_cto import apply_personal_cto_to_stories, build_personal_cto_brief
from ai_observatory.agents.personal_relevance import apply_personal_relevance
from ai_observatory.analysis import (
    analyze_stories as base_analyze_stories,
    build_briefing_payload as base_build_briefing_payload,
    categorize_story,
    ensure_story_urls,
)
from ai_observatory.config import settings
from ai_observatory.user_profile import UserProfile, load_user_profile


def enrich_stories(
    stories: list[dict[str, Any]], profile: UserProfile | None = None
) -> list[dict[str, Any]]:
    """Run Phase 2/3 deterministic agents on scored stories."""
    profile = profile or load_user_profile()
    enriched = ensure_story_urls(stories)
    enriched = tag_story_companies(enriched)
    enriched = tag_stories_with_industries(enriched)
    for story in enriched:
        story["category"] = categorize_story(story)
    enriched = apply_personal_relevance(enriched, profile)
    enriched = apply_career_impact(enriched, profile)
    enriched = apply_personal_cto_to_stories(enriched, profile)
    return enriched


def analyze_stories(
    stories: list[dict[str, Any]], top_n: int | None = None, profile: UserProfile | None = None
) -> list[dict[str, Any]]:
    """Score, enrich with Phase 2/3 agents, and return top stories."""
    top_n = top_n or settings.top_story_count
    scored = base_analyze_stories(stories, top_n=top_n * 2)
    enriched = enrich_stories(scored, profile)
    enriched.sort(key=lambda s: s.get("final_score", s.get("relevance_score", 0)), reverse=True)
    return enriched[:top_n]


def build_phase3_intelligence(
    stories: list[dict[str, Any]],
    profile: UserProfile | None = None,
    briefing_date: date | None = None,
) -> dict[str, Any]:
    """Build Phase 3 intelligence bundle for persistence and email."""
    profile = profile or load_user_profile()
    briefing_date = briefing_date or date.today()

    job_market = build_daily_job_market_summary(stories, briefing_date)
    enterprise_adoption = build_enterprise_adoption_report(stories, briefing_date)
    personal_cto = build_personal_cto_brief(
        stories,
        profile=profile,
        job_market=job_market,
        enterprise_adoption=enterprise_adoption,
    )

    return {
        "job_market": job_market,
        "enterprise_adoption": enterprise_adoption,
        "personal_cto": personal_cto,
    }


def build_briefing_payload(
    stories: list[dict[str, Any]],
    profile: UserProfile | None = None,
    briefing_date: date | None = None,
) -> dict[str, Any]:
    """Build briefing payload including Phase 2/3 intelligence."""
    profile = profile or load_user_profile()
    payload = base_build_briefing_payload(stories)
    payload["company_intelligence"] = build_company_intelligence(stories)
    payload["profile_name"] = profile.name
    payload["profile_roles"] = profile.roles

    phase3 = build_phase3_intelligence(stories, profile, briefing_date)
    payload.update(phase3)

    # Merge CTO actions with base recommended actions (deduplicated)
    cto_actions = phase3["personal_cto"].get("recommended_actions", [])
    merged_actions = list(dict.fromkeys(cto_actions + payload.get("recommended_actions", [])))
    payload["recommended_actions"] = merged_actions[:6]

    cto_summary = phase3["personal_cto"].get("executive_summary", "")
    payload["executive_summary"] = f"{payload['executive_summary']} {cto_summary}".strip()

    return payload


def intelligence_bundle_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract intelligence JSON for SQLite persistence (backward compatible)."""
    return {
        "company_intelligence": payload.get("company_intelligence", {}),
        "job_market": payload.get("job_market", {}),
        "enterprise_adoption": payload.get("enterprise_adoption", {}),
        "personal_cto": payload.get("personal_cto", {}),
    }
