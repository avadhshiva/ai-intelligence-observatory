"""Startup diagnostics for runtime dependency visibility."""

from __future__ import annotations

import importlib.metadata

from ai_observatory.config import settings
from ai_observatory.logging_setup import logger


def _pkg_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def log_startup_diagnostics() -> dict[str, str]:
    """Log and return key runtime versions and configuration."""
    info = {
        "crewai_version": _pkg_version("crewai"),
        "openai_version": _pkg_version("openai"),
        "active_model": settings.openai_model,
        "use_llm": str(settings.use_llm).lower(),
        "openai_api_key_configured": str(bool(settings.openai_api_key)).lower(),
    }
    logger.info("Startup diagnostics", extra=info)
    return info
