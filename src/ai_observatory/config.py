"""Application configuration loaded from environment variables."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)


def _parse_recipients(raw: str | None) -> list[str]:
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("["):
        try:
            return [e.strip() for e in json.loads(raw) if e.strip()]
        except json.JSONDecodeError:
            pass
    return [e.strip() for e in raw.split(",") if e.strip()]


@dataclass
class Settings:
    """Runtime settings for the observatory."""

    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    newsapi_key: str = field(default_factory=lambda: os.getenv("NEWSAPI_KEY", ""))

    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", f"sqlite:///{DATA_DIR / 'observatory.db'}"
        )
    )

    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "smtp.gmail.com"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    email_from: str = field(default_factory=lambda: os.getenv("EMAIL_FROM", ""))
    email_recipients: list[str] = field(
        default_factory=lambda: _parse_recipients(os.getenv("EMAIL_RECIPIENTS"))
    )

    schedule_hour: int = field(default_factory=lambda: int(os.getenv("SCHEDULE_HOUR", "7")))
    schedule_minute: int = field(default_factory=lambda: int(os.getenv("SCHEDULE_MINUTE", "0")))
    schedule_timezone: str = field(
        default_factory=lambda: os.getenv("SCHEDULE_TIMEZONE", "America/New_York")
    )

    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    use_llm: bool = field(
        default_factory=lambda: os.getenv("USE_LLM", "true").lower() in ("1", "true", "yes")
    )

    newsapi_query: str = field(
        default_factory=lambda: os.getenv(
            "NEWSAPI_QUERY",
            "artificial intelligence OR OpenAI OR Anthropic OR DeepMind OR NVIDIA AI",
        )
    )
    max_raw_stories: int = field(default_factory=lambda: int(os.getenv("MAX_RAW_STORIES", "50")))
    top_story_count: int = field(default_factory=lambda: int(os.getenv("TOP_STORY_COUNT", "10")))


settings = Settings()
