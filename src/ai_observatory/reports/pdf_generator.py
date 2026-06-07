"""Weekly Executive PDF report generator."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from ai_observatory.agents.company_intelligence import TRACKED_COMPANIES, build_company_intelligence
from ai_observatory.agents.job_market import build_weekly_job_market_summary
from ai_observatory.agents.personal_cto import build_personal_cto_brief
from ai_observatory.config import DATA_DIR
from ai_observatory.database import (
    get_briefings_in_range,
    get_job_market_history,
    list_weekly_reports,
    save_weekly_pdf,
)
from ai_observatory.logging_setup import logger

REPORTS_DIR = DATA_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def _week_bounds(reference: date | None = None) -> tuple[date, date]:
    ref = reference or date.today()
    week_start = ref - timedelta(days=ref.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def _vendor_scorecards(stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    intel = build_company_intelligence(stories)
    cards = []
    for company in TRACKED_COMPANIES:
        data = intel["companies"].get(company, {})
        cards.append(
            {
                "company": company,
                "story_count": data.get("story_count", 0),
                "avg_relevance": data.get("avg_relevance", 0),
                "active": data.get("active", False),
            }
        )
    cards.sort(key=lambda c: c["story_count"], reverse=True)
    return cards


def build_weekly_pdf_payload(reference: date | None = None) -> dict[str, Any]:
    week_start, week_end = _week_bounds(reference)
    briefings = get_briefings_in_range(week_start, week_end)
    all_stories: list[dict[str, Any]] = []
    themes_counter: dict[str, int] = {}

    for b in briefings:
        all_stories.extend(b.get("stories", []))
        for theme in b.get("themes", []):
            themes_counter[theme] = themes_counter.get(theme, 0) + 1

    top_stories = sorted(
        all_stories,
        key=lambda s: s.get("final_score", s.get("relevance_score", 0)),
        reverse=True,
    )[:10]

    job_history = get_job_market_history(week_start, week_end)
    job_weekly = build_weekly_job_market_summary(job_history)

    weekly_reports = list_weekly_reports(limit=4)
    trend_report = next(
        (r["report"] for r in weekly_reports if r["week_start"] == week_start.isoformat()),
        None,
    )

    cto = build_personal_cto_brief(top_stories, job_market=job_weekly)

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "top_stories": top_stories,
        "trend_evolution": {
            "themes": sorted(themes_counter.items(), key=lambda x: x[1], reverse=True),
            "briefing_count": len(briefings),
            "story_count": len(all_stories),
            "weekly_summary": trend_report.get("executive_summary") if trend_report else "",
        },
        "vendor_scorecards": _vendor_scorecards(all_stories),
        "career_impact": [
            {
                "title": s.get("title", ""),
                "summary": s.get("career_impact_summary", s.get("enterprise_impact", "")),
            }
            for s in top_stories[:5]
        ],
        "recommended_actions": cto.get("recommended_actions", []),
        "skills_to_learn": cto.get("skills_to_learn", []),
        "job_market_weekly": job_weekly,
        "personal_cto_summary": cto.get("executive_summary", ""),
    }


def generate_weekly_pdf(reference: date | None = None) -> Path:
    """Generate weekly executive PDF and persist metadata."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas

    payload = build_weekly_pdf_payload(reference)
    week_start = payload["week_start"]
    pdf_path = REPORTS_DIR / f"executive_weekly_{week_start}.pdf"

    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter
    y = height - inch

    def line(text: str, size: int = 11, gap: float = 0.22) -> None:
        nonlocal y
        if y < inch:
            c.showPage()
            y = height - inch
        c.setFont("Helvetica", size)
        c.drawString(inch, y, text[:110])
        y -= gap * inch

    def heading(text: str) -> None:
        nonlocal y
        y -= 0.1 * inch
        line(text, size=14, gap=0.28)

    heading("Executive AI Intelligence Weekly Report")
    line(f"Week: {payload['week_start']} to {payload['week_end']}")
    line(payload.get("personal_cto_summary", ""))

    heading("Top Stories")
    for idx, story in enumerate(payload["top_stories"][:10], start=1):
        score = story.get("final_score", story.get("relevance_score", "N/A"))
        line(f"{idx}. [{score}/10] {story.get('title', '')}")
        if story.get("url"):
            line(f"   Source: {story['url']}", size=9)

    heading("Trend Evolution")
    trend = payload["trend_evolution"]
    line(f"Briefings: {trend.get('briefing_count', 0)} | Stories: {trend.get('story_count', 0)}")
    for theme, count in trend.get("themes", [])[:5]:
        line(f"- {theme}: {count}")

    heading("Vendor Scorecards")
    for card in payload["vendor_scorecards"]:
        status = "Active" if card["active"] else "Quiet"
        line(
            f"{card['company']}: {card['story_count']} stories, "
            f"avg {card['avg_relevance']} ({status})"
        )

    heading("Career Impact Highlights")
    for item in payload["career_impact"]:
        line(f"- {item['title'][:80]}")
        line(f"  {item['summary'][:100]}", size=9)

    heading("Job Market Weekly")
    line(payload["job_market_weekly"].get("summary", ""))

    heading("Recommended Actions")
    for action in payload["recommended_actions"]:
        line(f"- {action}")

    heading("Skills To Learn")
    for skill in payload["skills_to_learn"]:
        line(f"- {skill}")

    c.save()
    save_weekly_pdf(week_start=date.fromisoformat(week_start), pdf_path=str(pdf_path), payload=payload)
    logger.info("Weekly PDF generated", extra={"path": str(pdf_path)})
    return pdf_path
