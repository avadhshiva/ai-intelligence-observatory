"""Pipeline helpers for persisting briefings and intelligence."""

from __future__ import annotations

from datetime import date
from typing import Any

from ai_observatory.agents.weekly_trends import generate_weekly_report, persist_daily_intelligence
from ai_observatory.database import (
    save_enterprise_adoption_snapshot,
    save_job_market_snapshot,
)
from ai_observatory.logging_setup import logger
from ai_observatory.reports.pdf_generator import generate_weekly_pdf
from ai_observatory.database import save_briefing


def finalize_briefing(
    briefing_date: date,
    subject: str,
    html_body: str,
    stories: list[dict[str, Any]],
    themes: list[str],
    actions: list[str],
    email_sent: bool = False,
    intelligence: dict[str, Any] | None = None,
    persist_trends: bool = True,
    generate_weekly: bool = True,
) -> int:
    intelligence = intelligence or {}
    briefing_id = save_briefing(
        briefing_date=briefing_date,
        subject=subject,
        html_body=html_body,
        stories=stories,
        themes=themes,
        actions=actions,
        email_sent=email_sent,
        intelligence=intelligence,
    )

    if persist_trends:
        company_intel = intelligence.get("company_intelligence", {})
        persist_daily_intelligence(briefing_date, stories, themes, company_intel)

        if intelligence.get("job_market"):
            save_job_market_snapshot(briefing_date, intelligence["job_market"])
        if intelligence.get("enterprise_adoption"):
            save_enterprise_adoption_snapshot(briefing_date, intelligence["enterprise_adoption"])

    weekly_report_id = None
    pdf_path = None
    if generate_weekly and briefing_date.weekday() == 6:  # Sunday
        report = generate_weekly_report(briefing_date)
        weekly_report_id = report.get("week_start")
        try:
            pdf_path = str(generate_weekly_pdf(briefing_date))
        except Exception as exc:
            logger.warning("Weekly PDF generation failed", extra={"error": str(exc)})

    logger.info(
        "Briefing saved",
        extra={
            "briefing_id": briefing_id,
            "date": briefing_date.isoformat(),
            "story_count": len(stories),
            "email_sent": email_sent,
            "weekly_report": weekly_report_id,
            "weekly_pdf": pdf_path,
        },
    )
    return briefing_id
