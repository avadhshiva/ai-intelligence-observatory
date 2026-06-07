"""Structured logging setup."""

from __future__ import annotations

import logging
import sys

from ai_observatory.config import settings


def _build_formatter() -> logging.Formatter:
    try:
        from pythonjsonlogger.json import JsonFormatter

        return JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
    except ImportError:
        return logging.Formatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logging() -> logging.Logger:
    """Configure structured logging to stdout; falls back to plain text if JSON logger missing."""
    app_logger = logging.getLogger("ai_observatory")
    if app_logger.handlers:
        return app_logger

    app_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_build_formatter())
    app_logger.addHandler(handler)
    app_logger.propagate = False
    return app_logger


logger = setup_logging()
