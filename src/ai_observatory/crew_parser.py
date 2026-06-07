"""CrewAI output capture, JSON repair, validation, and metrics."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from json_repair import repair_json

from ai_observatory.config import PROJECT_ROOT
from ai_observatory.crew_metrics import persist_raw_crew_output, record_crew_parse_run
from ai_observatory.logging_setup import logger
from ai_observatory.schemas.crew_output import CrewBriefingSchema

LOGS_DIR = PROJECT_ROOT / "logs"
RAW_OUTPUT_PATH = LOGS_DIR / "raw_crewai_output.json"
MAX_RAW_HISTORY = 50


@dataclass
class ParseResult:
    success: bool
    used_fallback: bool
    parse_status: str
    parse_error: str | None
    repair_steps: list[str] = field(default_factory=list)
    raw_output: str = ""
    validated_data: dict[str, Any] | None = None
    execution_time_ms: float = 0.0
    token_usage: dict[str, Any] = field(default_factory=dict)


def extract_crew_result_payload(result: Any) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    """Extract raw text, token usage, and optional pre-parsed json_dict from CrewOutput."""
    token_usage: dict[str, Any] = {}
    json_dict: dict[str, Any] | None = None
    raw = str(result)

    if hasattr(result, "token_usage") and result.token_usage is not None:
        usage = result.token_usage
        if hasattr(usage, "model_dump"):
            token_usage = usage.model_dump()
        elif isinstance(usage, dict):
            token_usage = usage

    if hasattr(result, "json_dict") and isinstance(result.json_dict, dict):
        json_dict = result.json_dict

    if hasattr(result, "raw") and result.raw:
        raw = result.raw

    return raw, token_usage, json_dict


def repair_json_text(raw: str) -> tuple[str, list[str]]:
    """Apply deterministic JSON repairs before parsing."""
    steps: list[str] = []
    text = raw.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json|JSON)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
        steps.append("stripped_markdown_fences")

    # Smart/curly quotes → straight quotes
    if any(ch in text for ch in ("\u201c", "\u201d", "\u2018", "\u2019")):
        text = (
            text.replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("\u2018", "'")
            .replace("\u2019", "'")
        )
        steps.append("normalized_smart_quotes")

    # Literal escaped newlines outside valid JSON strings
    if "\\n" in text and "\n" not in text[:200]:
        text = text.replace("\\n", "\n")
        steps.append("unescaped_newlines")

    # Trailing commas before } or ]
    trailing_before = text
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    if text != trailing_before:
        steps.append("removed_trailing_commas")

    # Fix common malformed quote patterns: ""key"" -> "key"
    text = re.sub(r'""(\w+)""\s*:', r'"\1":', text)
    if '""' in trailing_before and '""' not in text:
        steps.append("fixed_malformed_quotes")

    return text.strip(), steps


def _loads_json(text: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed, None
        return None, "JSON root is not an object"
    except json.JSONDecodeError as exc:
        return None, str(exc)


def parse_json_with_repair(raw: str) -> tuple[dict[str, Any] | None, list[str], str | None]:
    """Parse JSON with progressive repair strategies."""
    repair_steps: list[str] = []

    # Direct parse
    data, err = _loads_json(raw)
    if data is not None:
        return data, repair_steps, None

    # Custom repairs
    repaired, steps = repair_json_text(raw)
    repair_steps.extend(steps)
    data, err = _loads_json(repaired)
    if data is not None:
        return data, repair_steps, None

    # Extract JSON object substring
    match = re.search(r"\{.*\}", repaired, re.DOTALL)
    if match:
        data, err = _loads_json(match.group())
        if data is not None:
            repair_steps.append("extracted_json_object")
            return data, repair_steps, None

    # json_repair library fallback
    try:
        repaired_lib = repair_json(repaired)
        if isinstance(repaired_lib, str):
            data, err = _loads_json(repaired_lib)
        elif isinstance(repaired_lib, dict):
            data, err = repaired_lib, None
        else:
            data, err = None, "json_repair returned non-object"
        if data is not None:
            repair_steps.append("json_repair_library")
            return data, repair_steps, None
    except Exception as exc:
        err = f"json_repair failed: {exc}"

    return None, repair_steps, err or "Unknown JSON parse failure"


def validate_briefing_data(data: dict[str, Any]) -> tuple[CrewBriefingSchema | None, str | None]:
    try:
        return CrewBriefingSchema.model_validate(data), None
    except Exception as exc:
        return None, str(exc)


def save_raw_output_record(
    raw_output: str,
    parse_status: str,
    parse_error: str | None,
    token_usage: dict[str, Any],
    execution_time_ms: float,
    repair_steps: list[str],
) -> None:
    """Persist raw CrewAI output to logs/raw_crewai_output.json."""
    LOGS_DIR.mkdir(exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "parse_status": parse_status,
        "parse_error": parse_error,
        "execution_time_ms": execution_time_ms,
        "repair_steps": repair_steps,
        "token_usage": token_usage,
        "raw_output": raw_output,
    }

    history: list[dict[str, Any]] = []
    if RAW_OUTPUT_PATH.exists():
        try:
            history = json.loads(RAW_OUTPUT_PATH.read_text(encoding="utf-8"))
            if not isinstance(history, list):
                history = [history]
        except json.JSONDecodeError:
            history = []

    history.append(record)
    history = history[-MAX_RAW_HISTORY:]
    RAW_OUTPUT_PATH.write_text(json.dumps(history, indent=2, default=str), encoding="utf-8")
    persist_raw_crew_output(record)


def parse_crew_output(
    result: Any,
    execution_time_ms: float,
) -> ParseResult:
    """
    Capture, repair, validate, and metricize CrewAI output.

    Returns ParseResult with validated_data when parsing succeeds.
    """
    raw, token_usage, json_dict = extract_crew_result_payload(result)

    # Prefer CrewAI-native json_dict when present
    if json_dict and "stories" in json_dict:
        validated, val_err = validate_briefing_data(json_dict)
        if validated:
            save_raw_output_record(
                raw_output=raw,
                parse_status="success",
                parse_error=None,
                token_usage=token_usage,
                execution_time_ms=execution_time_ms,
                repair_steps=["crew_json_dict"],
            )
            record_crew_parse_run(
                parse_status="success",
                used_fallback=False,
                parse_error=None,
                execution_time_ms=execution_time_ms,
                token_usage=token_usage,
                repair_steps=["crew_json_dict"],
                raw_preview=raw[:500],
            )
            return ParseResult(
                success=True,
                used_fallback=False,
                parse_status="success",
                parse_error=None,
                repair_steps=["crew_json_dict"],
                raw_output=raw,
                validated_data=validated.model_dump(),
                execution_time_ms=execution_time_ms,
                token_usage=token_usage,
            )

    data, repair_steps, parse_error = parse_json_with_repair(raw)
    if data is None:
        reason = parse_error or "JSON parse failed"
        logger.error("CrewAI parse failed", extra={"reason": reason, "repair_steps": repair_steps})
        save_raw_output_record(
            raw_output=raw,
            parse_status="failed",
            parse_error=reason,
            token_usage=token_usage,
            execution_time_ms=execution_time_ms,
            repair_steps=repair_steps,
        )
        record_crew_parse_run(
            parse_status="failed",
            used_fallback=True,
            parse_error=reason,
            execution_time_ms=execution_time_ms,
            token_usage=token_usage,
            repair_steps=repair_steps,
            raw_preview=raw[:500],
        )
        return ParseResult(
            success=False,
            used_fallback=True,
            parse_status="failed",
            parse_error=reason,
            repair_steps=repair_steps,
            raw_output=raw,
            execution_time_ms=execution_time_ms,
            token_usage=token_usage,
        )

    validated, val_error = validate_briefing_data(data)
    if validated is None:
        reason = f"Pydantic validation failed: {val_error}"
        logger.error("CrewAI validation failed", extra={"reason": reason, "repair_steps": repair_steps})
        save_raw_output_record(
            raw_output=raw,
            parse_status="validation_failed",
            parse_error=reason,
            token_usage=token_usage,
            execution_time_ms=execution_time_ms,
            repair_steps=repair_steps,
        )
        record_crew_parse_run(
            parse_status="validation_failed",
            used_fallback=True,
            parse_error=reason,
            execution_time_ms=execution_time_ms,
            token_usage=token_usage,
            repair_steps=repair_steps,
            raw_preview=raw[:500],
        )
        return ParseResult(
            success=False,
            used_fallback=True,
            parse_status="validation_failed",
            parse_error=reason,
            repair_steps=repair_steps,
            raw_output=raw,
            execution_time_ms=execution_time_ms,
            token_usage=token_usage,
        )

    status = "repaired" if repair_steps else "success"
    save_raw_output_record(
        raw_output=raw,
        parse_status=status,
        parse_error=None,
        token_usage=token_usage,
        execution_time_ms=execution_time_ms,
        repair_steps=repair_steps,
    )
    record_crew_parse_run(
        parse_status=status,
        used_fallback=False,
        parse_error=None,
        execution_time_ms=execution_time_ms,
        token_usage=token_usage,
        repair_steps=repair_steps,
        raw_preview=raw[:500],
    )
    logger.info(
        "CrewAI output parsed",
        extra={"parse_status": status, "repair_steps": repair_steps, "stories": len(validated.stories)},
    )
    return ParseResult(
        success=True,
        used_fallback=False,
        parse_status=status,
        parse_error=None,
        repair_steps=repair_steps,
        raw_output=raw,
        validated_data=validated.model_dump(),
        execution_time_ms=execution_time_ms,
        token_usage=token_usage,
    )


class CrewExecutionTimer:
    """Context manager for CrewAI execution timing."""

    def __enter__(self) -> CrewExecutionTimer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    @property
    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000
