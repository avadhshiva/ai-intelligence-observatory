# Dependency Audit Report — AI Intelligence Observatory

Generated: 2026-06-06

## Scope

Recursive scan of `src/`, `dashboard/`, `tests/` (35 Python files, excluding `.venv`).

## Runtime Dependencies (declared)

| Package | Used in code | In pyproject.toml | In requirements.txt |
|---------|--------------|-------------------|---------------------|
| crewai | `crew.py` | yes | yes |
| feedparser | `collectors/news_collector.py` | yes | yes |
| httpx | `collectors/news_collector.py` | yes | yes |
| jinja2 | `email_service.py` | yes | yes |
| json-repair | `crew_parser.py` | yes | yes |
| pandas | `dashboard/app.py` | yes | yes |
| plotly | `dashboard/app.py` | yes | yes |
| pydantic | `schemas/crew_output.py` | yes | yes |
| python-dotenv | `config.py` | yes | yes |
| python-json-logger | `logging_setup.py` (optional fallback) | yes | yes |
| reportlab | `reports/pdf_generator.py` (lazy) | yes | yes |
| sqlalchemy | `database.py`, `crew_metrics.py` | yes | yes |
| streamlit | `dashboard/app.py` | yes | yes |
| apscheduler | `scheduler.py` | yes | yes |

## Dev Dependencies

| Package | Used in code | In requirements-dev.txt |
|---------|--------------|---------------------------|
| pytest | all test modules | yes |
| pytest-mock | declared only | yes (optional; tests use unittest.mock) |

## Removed / Not Used

| Package | Status |
|---------|--------|
| crewai-tools | Removed in prior audit — never imported |
| newsapi-python | Removed in prior audit — collector uses httpx directly |
| beautifulsoup4 | Not used — HTML stripped via regex |
| requests | Not used — httpx used instead |

## Missing Packages Fixed

| Issue | Resolution |
|-------|------------|
| `pydantic` imported but undeclared | Added to pyproject.toml and requirements.txt |
| `json-repair` missing from requirements.txt | Added (synced with pyproject.toml) |
| `pytest` in runtime requirements.txt | Moved to requirements-dev.txt |

## Deprecated Streamlit APIs Fixed

| Location | Before | After |
|----------|--------|-------|
| `dashboard/app.py` (13 sites) | `use_container_width=True` | `width="stretch"` |
| `dashboard/app.py` line 162 | `components.v1.html(...)` | `st.html(..., width="stretch")` |
| `dashboard/app.py` imports | `import streamlit.components.v1 as components` | removed |

## Unresolved Imports

**None** — all 25 application modules and dashboard import chain resolve successfully (`scripts/audit_imports.py`, `scripts/health_check.py`).

## Runtime Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| OPENAI_API_KEY unset | Low | Deterministic fallback when `USE_LLM=false` or key missing |
| SMTP not configured | Low | Email skipped; briefing still saved to SQLite |
| CrewAI heavy import | Low | Lazy import via `_crewai_types()` in `crew.py` |
| python-json-logger missing | Low | Falls back to plain `logging.Formatter` |
| RSS feed failures | Low | Per-feed try/except; pipeline continues |
| `st.html` requires Streamlit ≥1.33 | Low | Pinned `streamlit>=1.40.0` |

## Recommended Improvements

1. Add CI step: `python scripts/health_check.py && pytest tests/`
2. Pin upper bounds on major deps in a separate lock file (`requirements.lock.txt` already exists)
3. Consider removing unused `pytest-mock` from dev deps
4. Add `.env.example` documenting all optional config keys
5. Wrap `st.html` email preview in a max-height container if scrolling is needed for long briefings

## Validation Results

| Check | Result |
|-------|--------|
| `python -m compileall src` | PASS |
| `python -m compileall dashboard` | PASS |
| `python scripts/health_check.py` | PASS |
| `pytest tests/` | 37 passed |
| `streamlit run dashboard/app.py` | PASS (headless startup) |

## Install

```powershell
pip install -r requirements.txt
pip install -r requirements-dev.txt   # tests only
python scripts/health_check.py
streamlit run dashboard/app.py
```
