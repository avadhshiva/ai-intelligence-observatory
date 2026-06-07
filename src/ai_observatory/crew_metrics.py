"""CrewAI parse metrics persistence and reporting."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func

from ai_observatory.database import Base
import ai_observatory.database as db


class CrewParseRun(Base):
    __tablename__ = "crew_parse_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    parse_status = Column(String(64), nullable=False)
    used_fallback = Column(Integer, nullable=False, default=0)
    parse_error = Column(Text, nullable=True)
    execution_time_ms = Column(Float, nullable=False, default=0.0)
    token_usage_json = Column(Text, nullable=False, default="{}")
    repair_steps_json = Column(Text, nullable=False, default="[]")
    raw_preview = Column(Text, nullable=False, default="")


class RawCrewOutputRecord(Base):
    __tablename__ = "raw_crew_outputs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    captured_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    payload_json = Column(Text, nullable=False)


def record_crew_parse_run(
    parse_status: str,
    used_fallback: bool,
    parse_error: str | None,
    execution_time_ms: float,
    token_usage: dict[str, Any],
    repair_steps: list[str],
    raw_preview: str,
) -> None:
    db.init_db()
    with db.SessionLocal() as session:
        session.add(
            CrewParseRun(
                parse_status=parse_status,
                used_fallback=1 if used_fallback else 0,
                parse_error=parse_error,
                execution_time_ms=execution_time_ms,
                token_usage_json=json.dumps(token_usage),
                repair_steps_json=json.dumps(repair_steps),
                raw_preview=raw_preview,
            )
        )
        session.commit()


def persist_raw_crew_output(record: dict[str, Any]) -> None:
    db.init_db()
    with db.SessionLocal() as session:
        session.add(RawCrewOutputRecord(payload_json=json.dumps(record, default=str)))
        session.commit()


def list_crew_parse_runs(limit: int = 50) -> list[dict[str, Any]]:
    db.init_db()
    with db.SessionLocal() as session:
        rows = session.query(CrewParseRun).order_by(CrewParseRun.run_at.desc()).limit(limit).all()
        return [
            {
                "run_at": r.run_at.isoformat() if r.run_at else None,
                "parse_status": r.parse_status,
                "used_fallback": bool(r.used_fallback),
                "parse_error": r.parse_error,
                "execution_time_ms": r.execution_time_ms,
                "token_usage": json.loads(r.token_usage_json),
                "repair_steps": json.loads(r.repair_steps_json),
                "raw_preview": r.raw_preview,
            }
            for r in rows
        ]


def get_crew_diagnostics_summary() -> dict[str, Any]:
    db.init_db()
    with db.SessionLocal() as session:
        rows = session.query(CrewParseRun).order_by(CrewParseRun.run_at.desc()).limit(200).all()

    total = len(rows)
    if total == 0:
        return {
            "total_runs": 0,
            "success_rate": 0.0,
            "fallback_rate": 0.0,
            "avg_execution_time_ms": 0.0,
            "total_tokens": 0,
            "avg_tokens_per_run": 0,
        }

    successes = sum(
        1 for r in rows if r.parse_status in ("success", "repaired") and not r.used_fallback
    )
    fallbacks = sum(1 for r in rows if r.used_fallback)
    avg_time = sum(r.execution_time_ms for r in rows) / total
    total_tokens = sum(json.loads(r.token_usage_json).get("total_tokens", 0) for r in rows)

    return {
        "total_runs": total,
        "success_rate": round(successes / total * 100, 1),
        "fallback_rate": round(fallbacks / total * 100, 1),
        "avg_execution_time_ms": round(avg_time, 1),
        "total_tokens": total_tokens,
        "avg_tokens_per_run": round(total_tokens / total, 1) if total else 0,
    }


def load_raw_crew_output_file() -> list[dict[str, Any]]:
    from ai_observatory.crew_parser import RAW_OUTPUT_PATH

    if not RAW_OUTPUT_PATH.exists():
        return []
    try:
        data = json.loads(RAW_OUTPUT_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        return []
