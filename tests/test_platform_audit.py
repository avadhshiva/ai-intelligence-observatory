"""Platform audit tests — logging fallback and dependency imports."""

from __future__ import annotations

import importlib
import logging
import sys


def test_logging_fallback_without_json_logger(monkeypatch):
    """Dashboard must not fail if python-json-logger is unavailable."""
    monkeypatch.setitem(sys.modules, "pythonjsonlogger", None)
    monkeypatch.setitem(sys.modules, "pythonjsonlogger.json", None)

    import ai_observatory.logging_setup as logging_setup

    importlib.reload(logging_setup)
    assert logging_setup.logger.handlers
    assert isinstance(logging_setup.logger.handlers[0].formatter, logging.Formatter)


def test_crew_module_exports_run_observatory_crew():
    import ai_observatory.crew as crew_mod

    assert hasattr(crew_mod, "run_observatory_crew")
    assert callable(crew_mod.run_observatory_crew)
    assert hasattr(crew_mod, "_crewai_types")
