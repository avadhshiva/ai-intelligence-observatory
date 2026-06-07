# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-06

### Added

- CrewAI multi-agent pipeline (Scout → Analyst → Executive → Email)
- Executive AI daily briefing generation
- Gmail SMTP email delivery with responsive HTML templates
- Streamlit executive dashboard with 11 tabs
- SQLite persistence for briefings, trends, and intelligence snapshots
- Personal relevance, company intelligence, and career impact agents
- Job market, enterprise adoption, and personal CTO intelligence layers
- Weekly trend reports and executive PDF generation
- CrewAI output diagnostics tab with parse metrics and token usage
- JSON repair pipeline for CrewAI output (markdown fences, trailing commas, malformed quotes)
- Pydantic schema validation for CrewAI briefing output
- Raw CrewAI output capture to `logs/raw_crewai_output.json`
- Deterministic fallback when LLM parsing fails or `USE_LLM=false`
- Health check script (`scripts/health_check.py`)
- GitHub Actions CI workflow (pytest + health check)
- GitHub Actions daily briefing workflow (06:00 IST cron)
- Deployment and repository audit documentation

### Changed

- Streamlit API modernization (`width="stretch"`, `st.html`)
- Lazy CrewAI imports for faster dashboard startup
- Graceful logging fallback when `python-json-logger` unavailable

[1.0.0]: https://github.com/YOUR_ORG/ai-intelligence-observatory/releases/tag/v1.0.0
