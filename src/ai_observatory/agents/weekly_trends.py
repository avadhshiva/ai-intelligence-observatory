"""Weekly Trend Agent — persist themes and generate weekly reports."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any

from ai_observatory.agents.company_intelligence import TRACKED_COMPANIES, build_company_intelligence
from ai_observatory.agents.job_market import build_weekly_job_market_summary
from ai_observatory.analysis import extract_themes, categorize_story
from ai_observatory.database import (
    get_briefings_in_range,
    get_job_market_history,
    get_theme_history,
    save_theme_snapshots,
    save_weekly_report,
)
from ai_observatory.logging_setup import logger


def persist_daily_intelligence(
    briefing_date: date,
    stories: list[dict[str, Any]],
    themes: list[str],
    company_intel: dict[str, Any],
) -> None:
    """Persist daily themes, categories, and company activity to SQLite."""
    theme_counts = Counter(themes)
    for theme in themes:
        theme_counts[theme] += 0  # ensure theme exists

    category_counts: Counter[str] = Counter()
    company_counts: Counter[str] = Counter()
    for story in stories:
        category = story.get("category") or categorize_story(story)
        category_counts[category] += 1
        for company in story.get("companies", []):
            company_counts[company] += 1

    snapshots = []
    for theme, count in theme_counts.items():
        snapshots.append({"theme": theme, "count": max(count, 1)})

    save_theme_snapshots(
        briefing_date=briefing_date,
        themes=snapshots,
        categories=dict(category_counts),
        company_activity={
            company: company_intel["companies"].get(company, {}).get("story_count", count)
            for company, count in company_counts.items()
        },
    )
    logger.info(
        "Daily intelligence persisted",
        extra={
            "date": briefing_date.isoformat(),
            "themes": len(snapshots),
            "categories": len(category_counts),
        },
    )


def _week_bounds(reference: date | None = None) -> tuple[date, date]:
    ref = reference or date.today()
    week_start = ref - timedelta(days=ref.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def generate_weekly_report(reference: date | None = None) -> dict[str, Any]:
    """Generate and persist a weekly trend report from stored briefings."""
    week_start, week_end = _week_bounds(reference)
    briefings = get_briefings_in_range(week_start, week_end)
    theme_history = get_theme_history(week_start, week_end)

    theme_counter: Counter[str] = Counter()
    category_counter: Counter[str] = Counter()
    company_counter: Counter[str] = Counter()
    all_stories: list[dict[str, Any]] = []

    for row in theme_history:
        theme_counter[row["theme"]] += row["count"]
        for category, count in row.get("categories", {}).items():
            category_counter[category] += count
        for company, count in row.get("company_activity", {}).items():
            company_counter[company] += count

    for briefing in briefings:
        all_stories.extend(briefing.get("stories", []))

    company_intel = build_company_intelligence(all_stories)
    rising_themes = [t for t, _ in theme_counter.most_common(5)]
    top_categories = [c for c, _ in category_counter.most_common(5)]
    active_companies = [c for c, _ in company_counter.most_common() if c in TRACKED_COMPANIES]

    job_weekly = build_weekly_job_market_summary(get_job_market_history(week_start, week_end))

    report = {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "briefing_count": len(briefings),
        "story_count": sum(b.get("story_count", 0) for b in briefings),
        "rising_themes": rising_themes,
        "theme_frequency": dict(theme_counter),
        "top_categories": top_categories,
        "category_frequency": dict(category_counter),
        "company_activity": dict(company_counter),
        "most_active_companies": active_companies[:3],
        "company_intelligence": company_intel,
        "job_market_weekly": job_weekly,
        "executive_summary": (
            f"Week of {week_start.isoformat()}: {len(briefings)} briefings covering "
            f"{sum(b.get('story_count', 0) for b in briefings)} stories. "
            f"Top themes: {', '.join(rising_themes[:3]) or 'N/A'}. "
            f"Most active companies: {', '.join(active_companies[:3]) or 'N/A'}. "
            f"{job_weekly.get('summary', '')}"
        ),
        "recommended_actions": [
            "Compare this week's rising themes against your program OKRs.",
            "Brief leadership on vendor activity shifts among priority AI companies.",
            "Update your transformation roadmap based on category momentum.",
        ],
    }

    save_weekly_report(week_start, week_end, report)
    logger.info("Weekly report generated", extra={"week_start": week_start.isoformat()})
    return report
