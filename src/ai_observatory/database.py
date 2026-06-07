"""Data models and persistence layer."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ai_observatory.config import settings


class Base(DeclarativeBase):
    pass


class BriefingRecord(Base):
    __tablename__ = "briefings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    briefing_date = Column(Date, unique=True, nullable=False, index=True)
    subject = Column(String(512), nullable=False)
    html_body = Column(Text, nullable=False)
    stories_json = Column(Text, nullable=False)
    themes_json = Column(Text, nullable=False)
    actions_json = Column(Text, nullable=False)
    intelligence_json = Column(Text, nullable=False, default="{}")
    story_count = Column(Integer, nullable=False, default=0)
    avg_relevance = Column(Float, nullable=True)
    email_sent = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class ThemeSnapshot(Base):
    __tablename__ = "theme_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    briefing_date = Column(Date, nullable=False, index=True)
    theme = Column(String(256), nullable=False, index=True)
    story_count = Column(Integer, nullable=False, default=1)
    categories_json = Column(Text, nullable=False, default="{}")
    company_activity_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class WeeklyReportRecord(Base):
    __tablename__ = "weekly_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    week_start = Column(Date, unique=True, nullable=False, index=True)
    week_end = Column(Date, nullable=False)
    report_json = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class JobMarketSnapshot(Base):
    __tablename__ = "job_market_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(Date, unique=True, nullable=False, index=True)
    snapshot_json = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class EnterpriseAdoptionSnapshot(Base):
    __tablename__ = "enterprise_adoption_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(Date, unique=True, nullable=False, index=True)
    snapshot_json = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class WeeklyPdfRecord(Base):
    __tablename__ = "weekly_pdf_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    week_start = Column(Date, unique=True, nullable=False, index=True)
    pdf_path = Column(String(2048), nullable=False)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class StoryRecord(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    briefing_id = Column(Integer, nullable=False, index=True)
    title = Column(String(1024), nullable=False)
    url = Column(String(2048), nullable=False)
    source = Column(String(256), nullable=False)
    relevance_score = Column(Float, nullable=False)
    why_it_matters = Column(Text, nullable=False)
    enterprise_impact = Column(Text, nullable=False)
    published_at = Column(DateTime, nullable=True)


engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    import ai_observatory.crew_metrics  # noqa: F401 — register Phase 3/crew metric tables

    Base.metadata.create_all(bind=engine)
    _migrate_schema()


def _migrate_schema() -> None:
    """Add Phase 2 columns/tables to existing SQLite databases."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "briefings" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("briefings")}
    if "intelligence_json" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE briefings ADD COLUMN intelligence_json TEXT NOT NULL DEFAULT '{}'")
            )


def save_briefing(
    briefing_date: date,
    subject: str,
    html_body: str,
    stories: list[dict[str, Any]],
    themes: list[str],
    actions: list[str],
    email_sent: bool = False,
    intelligence: dict[str, Any] | None = None,
) -> int:
    """Persist a daily briefing and its stories. Returns briefing id."""
    init_db()
    avg_score = (
        sum(s.get("final_score", s.get("relevance_score", 0)) for s in stories) / len(stories)
        if stories
        else 0.0
    )
    intelligence = intelligence or {}
    with SessionLocal() as session:
        existing = (
            session.query(BriefingRecord)
            .filter(BriefingRecord.briefing_date == briefing_date)
            .one_or_none()
        )
        if existing:
            session.query(StoryRecord).filter(StoryRecord.briefing_id == existing.id).delete()
            briefing = existing
            briefing.subject = subject
            briefing.html_body = html_body
            briefing.stories_json = json.dumps(stories)
            briefing.themes_json = json.dumps(themes)
            briefing.actions_json = json.dumps(actions)
            briefing.intelligence_json = json.dumps(intelligence)
            briefing.story_count = len(stories)
            briefing.avg_relevance = avg_score
            briefing.email_sent = 1 if email_sent else 0
        else:
            briefing = BriefingRecord(
                briefing_date=briefing_date,
                subject=subject,
                html_body=html_body,
                stories_json=json.dumps(stories),
                themes_json=json.dumps(themes),
                actions_json=json.dumps(actions),
                intelligence_json=json.dumps(intelligence),
                story_count=len(stories),
                avg_relevance=avg_score,
                email_sent=1 if email_sent else 0,
            )
            session.add(briefing)
            session.flush()

        for story in stories:
            pub = story.get("published_at")
            published_dt = None
            if pub:
                if isinstance(pub, datetime):
                    published_dt = pub
                else:
                    try:
                        published_dt = datetime.fromisoformat(str(pub).replace("Z", "+00:00"))
                    except ValueError:
                        published_dt = None

            session.add(
                StoryRecord(
                    briefing_id=briefing.id,
                    title=story.get("title", ""),
                    url=story.get("url", ""),
                    source=story.get("source", ""),
                    relevance_score=float(story.get("relevance_score", 0)),
                    why_it_matters=story.get("why_it_matters", ""),
                    enterprise_impact=story.get("enterprise_impact", ""),
                    published_at=published_dt,
                )
            )
        session.commit()
        return briefing.id


def list_briefings(limit: int = 30) -> list[dict[str, Any]]:
    init_db()
    with SessionLocal() as session:
        rows = (
            session.query(BriefingRecord)
            .order_by(BriefingRecord.briefing_date.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "briefing_date": r.briefing_date.isoformat(),
                "subject": r.subject,
                "story_count": r.story_count,
                "avg_relevance": r.avg_relevance,
                "email_sent": bool(r.email_sent),
                "themes": json.loads(r.themes_json),
                "actions": json.loads(r.actions_json),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


def get_briefing_by_date(briefing_date: date) -> dict[str, Any] | None:
    init_db()
    with SessionLocal() as session:
        row = (
            session.query(BriefingRecord)
            .filter(BriefingRecord.briefing_date == briefing_date)
            .one_or_none()
        )
        if not row:
            return None
        return {
            "id": row.id,
            "briefing_date": row.briefing_date.isoformat(),
            "subject": row.subject,
            "html_body": row.html_body,
            "stories": json.loads(row.stories_json),
            "themes": json.loads(row.themes_json),
            "actions": json.loads(row.actions_json),
            "intelligence": json.loads(getattr(row, "intelligence_json", None) or "{}"),
            "story_count": row.story_count,
            "avg_relevance": row.avg_relevance,
            "email_sent": bool(row.email_sent),
        }


def get_briefings_in_range(start: date, end: date) -> list[dict[str, Any]]:
    init_db()
    with SessionLocal() as session:
        rows = (
            session.query(BriefingRecord)
            .filter(BriefingRecord.briefing_date >= start, BriefingRecord.briefing_date <= end)
            .order_by(BriefingRecord.briefing_date.asc())
            .all()
        )
        return [
            {
                "briefing_date": r.briefing_date.isoformat(),
                "story_count": r.story_count,
                "avg_relevance": r.avg_relevance,
                "themes": json.loads(r.themes_json),
                "stories": json.loads(r.stories_json),
                "intelligence": json.loads(getattr(r, "intelligence_json", None) or "{}"),
            }
            for r in rows
        ]


def save_theme_snapshots(
    briefing_date: date,
    themes: list[dict[str, Any]],
    categories: dict[str, int],
    company_activity: dict[str, int],
) -> None:
    init_db()
    with SessionLocal() as session:
        session.query(ThemeSnapshot).filter(ThemeSnapshot.briefing_date == briefing_date).delete()
        for item in themes:
            session.add(
                ThemeSnapshot(
                    briefing_date=briefing_date,
                    theme=item["theme"],
                    story_count=int(item.get("count", 1)),
                    categories_json=json.dumps(categories),
                    company_activity_json=json.dumps(company_activity),
                )
            )
        session.commit()


def get_theme_history(start: date, end: date) -> list[dict[str, Any]]:
    init_db()
    with SessionLocal() as session:
        rows = (
            session.query(ThemeSnapshot)
            .filter(ThemeSnapshot.briefing_date >= start, ThemeSnapshot.briefing_date <= end)
            .order_by(ThemeSnapshot.briefing_date.asc())
            .all()
        )
        return [
            {
                "date": r.briefing_date.isoformat(),
                "theme": r.theme,
                "count": r.story_count,
                "categories": json.loads(r.categories_json),
                "company_activity": json.loads(r.company_activity_json),
            }
            for r in rows
        ]


def save_weekly_report(week_start: date, week_end: date, report: dict[str, Any]) -> int:
    init_db()
    with SessionLocal() as session:
        existing = (
            session.query(WeeklyReportRecord)
            .filter(WeeklyReportRecord.week_start == week_start)
            .one_or_none()
        )
        if existing:
            existing.week_end = week_end
            existing.report_json = json.dumps(report)
            session.commit()
            return existing.id
        row = WeeklyReportRecord(
            week_start=week_start,
            week_end=week_end,
            report_json=json.dumps(report),
        )
        session.add(row)
        session.commit()
        return row.id


def list_weekly_reports(limit: int = 12) -> list[dict[str, Any]]:
    init_db()
    with SessionLocal() as session:
        rows = (
            session.query(WeeklyReportRecord)
            .order_by(WeeklyReportRecord.week_start.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "week_start": r.week_start.isoformat(),
                "week_end": r.week_end.isoformat(),
                "report": json.loads(r.report_json),
            }
            for r in rows
        ]


def get_company_activity_history(days: int = 30) -> list[dict[str, Any]]:
    init_db()
    with SessionLocal() as session:
        rows = (
            session.query(BriefingRecord)
            .order_by(BriefingRecord.briefing_date.desc())
            .limit(days)
            .all()
        )
        history: list[dict[str, Any]] = []
        for row in reversed(rows):
            intel = json.loads(getattr(row, "intelligence_json", None) or "{}")
            companies = intel.get("company_intelligence", {}).get("companies", {})
            history.append(
                {
                    "date": row.briefing_date.isoformat(),
                    "companies": {
                        name: data.get("story_count", 0) for name, data in companies.items()
                    },
                }
            )
        return history


def get_category_history(days: int = 30) -> list[dict[str, Any]]:
    init_db()
    with SessionLocal() as session:
        rows = (
            session.query(BriefingRecord)
            .order_by(BriefingRecord.briefing_date.desc())
            .limit(days)
            .all()
        )
        history: list[dict[str, Any]] = []
        for row in reversed(rows):
            stories = json.loads(row.stories_json)
            counts: dict[str, int] = {}
            for story in stories:
                category = story.get("category", "General AI News")
                counts[category] = counts.get(category, 0) + 1
            history.append({"date": row.briefing_date.isoformat(), "categories": counts})
        return history


def get_trend_data(days: int = 30) -> list[dict[str, Any]]:
    init_db()
    with SessionLocal() as session:
        rows = (
            session.query(BriefingRecord)
            .order_by(BriefingRecord.briefing_date.desc())
            .limit(days)
            .all()
        )
        return [
            {
                "date": r.briefing_date.isoformat(),
                "story_count": r.story_count,
                "avg_relevance": r.avg_relevance or 0,
                "themes": json.loads(r.themes_json),
            }
            for r in reversed(rows)
        ]


def save_job_market_snapshot(snapshot_date: date, snapshot: dict[str, Any]) -> None:
    init_db()
    with SessionLocal() as session:
        existing = (
            session.query(JobMarketSnapshot)
            .filter(JobMarketSnapshot.snapshot_date == snapshot_date)
            .one_or_none()
        )
        if existing:
            existing.snapshot_json = json.dumps(snapshot)
        else:
            session.add(
                JobMarketSnapshot(snapshot_date=snapshot_date, snapshot_json=json.dumps(snapshot))
            )
        session.commit()


def get_job_market_history(start: date, end: date) -> list[dict[str, Any]]:
    init_db()
    with SessionLocal() as session:
        rows = (
            session.query(JobMarketSnapshot)
            .filter(JobMarketSnapshot.snapshot_date >= start, JobMarketSnapshot.snapshot_date <= end)
            .order_by(JobMarketSnapshot.snapshot_date.asc())
            .all()
        )
        return [json.loads(r.snapshot_json) for r in rows]


def get_latest_job_market_snapshot() -> dict[str, Any] | None:
    init_db()
    with SessionLocal() as session:
        row = (
            session.query(JobMarketSnapshot)
            .order_by(JobMarketSnapshot.snapshot_date.desc())
            .first()
        )
        return json.loads(row.snapshot_json) if row else None


def save_enterprise_adoption_snapshot(snapshot_date: date, snapshot: dict[str, Any]) -> None:
    init_db()
    with SessionLocal() as session:
        existing = (
            session.query(EnterpriseAdoptionSnapshot)
            .filter(EnterpriseAdoptionSnapshot.snapshot_date == snapshot_date)
            .one_or_none()
        )
        if existing:
            existing.snapshot_json = json.dumps(snapshot)
        else:
            session.add(
                EnterpriseAdoptionSnapshot(
                    snapshot_date=snapshot_date, snapshot_json=json.dumps(snapshot)
                )
            )
        session.commit()


def get_enterprise_adoption_history(days: int = 30) -> list[dict[str, Any]]:
    init_db()
    with SessionLocal() as session:
        rows = (
            session.query(EnterpriseAdoptionSnapshot)
            .order_by(EnterpriseAdoptionSnapshot.snapshot_date.desc())
            .limit(days)
            .all()
        )
        return [
            {"date": r.snapshot_date.isoformat(), **json.loads(r.snapshot_json)}
            for r in reversed(rows)
        ]


def get_latest_enterprise_adoption() -> dict[str, Any] | None:
    init_db()
    with SessionLocal() as session:
        row = (
            session.query(EnterpriseAdoptionSnapshot)
            .order_by(EnterpriseAdoptionSnapshot.snapshot_date.desc())
            .first()
        )
        if not row:
            return None
        return {"date": row.snapshot_date.isoformat(), **json.loads(row.snapshot_json)}


def save_weekly_pdf(week_start: date, pdf_path: str, payload: dict[str, Any]) -> int:
    init_db()
    with SessionLocal() as session:
        existing = (
            session.query(WeeklyPdfRecord)
            .filter(WeeklyPdfRecord.week_start == week_start)
            .one_or_none()
        )
        if existing:
            existing.pdf_path = pdf_path
            existing.payload_json = json.dumps(payload)
            session.commit()
            return existing.id
        row = WeeklyPdfRecord(
            week_start=week_start,
            pdf_path=pdf_path,
            payload_json=json.dumps(payload),
        )
        session.add(row)
        session.commit()
        return row.id


def list_weekly_pdfs(limit: int = 12) -> list[dict[str, Any]]:
    init_db()
    with SessionLocal() as session:
        rows = (
            session.query(WeeklyPdfRecord)
            .order_by(WeeklyPdfRecord.week_start.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "week_start": r.week_start.isoformat(),
                "pdf_path": r.pdf_path,
                "payload": json.loads(r.payload_json),
            }
            for r in rows
        ]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
