# Repository Audit — AI Intelligence Observatory

Generated: 2026-06-06  
Scope: Pre-publication hardening for GitHub and automated daily briefings.

## Git & Secrets

| Check | Status | Notes |
|-------|--------|-------|
| `.env` excluded | PASS | Listed in `.gitignore` |
| `.env.example` committed | PASS | Template without secrets |
| `.streamlit/secrets.toml` excluded | PASS | Listed in `.gitignore` |
| `data/` excluded | PASS | Added to `.gitignore` |
| `logs/` excluded | PASS | Listed in `.gitignore` |
| `.venv/` excluded | PASS | Listed in `.gitignore` |
| `__pycache__/` excluded | PASS | Listed in `.gitignore` |
| `config/user_profile.json` excluded | PASS | Added to `.gitignore`; remove from git index if previously tracked |
| Secrets in tracked files | PASS | No API keys found in source |

## Package Structure

| Check | Status |
|-------|--------|
| `src/ai_observatory/` layout | PASS |
| `pyproject.toml` valid | PASS |
| Entry point `ai-observatory` | PASS |
| Version aligned to release | PASS (`1.0.0`) |

## Dependencies

### Runtime (`requirements.txt` ↔ imports)

| Package | Used | Declared |
|---------|------|----------|
| crewai | yes | yes |
| feedparser | yes | yes |
| httpx | yes | yes |
| jinja2 | yes | yes |
| json-repair | yes | yes |
| pandas | yes | yes |
| plotly | yes | yes |
| pydantic | yes | yes |
| python-dotenv | yes | yes |
| python-json-logger | yes | yes |
| reportlab | yes | yes |
| sqlalchemy | yes | yes |
| streamlit | yes | yes |
| apscheduler | yes | yes |

### Missing dependencies

None identified.

### Unused dependencies

None in current runtime manifests (removed in prior audit: `crewai-tools`, `newsapi-python`).

### Dev dependencies (`requirements-dev.txt`)

| Package | Purpose |
|---------|---------|
| pytest | Test runner |
| pytest-mock | Optional (tests primarily use `unittest.mock`) |

## Security Concerns

| Item | Severity | Mitigation |
|------|----------|------------|
| Personal profile in git | Medium | `config/user_profile.json` now gitignored |
| GitHub Secrets for CI | Medium | Documented in `docs/deployment.md` |
| SMTP app passwords | Medium | Never commit; use GitHub Secrets |
| CrewAI raw output logs | Low | `logs/` gitignored; artifacts retained 14 days in CI |

## Deployment Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| CrewAI install time in CI | Medium | 45-minute workflow timeout |
| Missing `user_profile.json` on fresh clone | High | CI copies from `user_profile.example.json` |
| NewsAPI optional | Low | RSS feeds still populate briefings |
| SQLite not shared across runners | Low | DB uploaded as artifact after daily run |
| IST cron drift / DST | None | IST has no DST; 06:00 IST = 00:30 UTC fixed |

## Recommendations Before Publishing

1. Run `git rm --cached config/user_profile.json` if it was previously committed.
2. Configure all GitHub Secrets before enabling `daily-briefing.yml`.
3. Enable GitHub Actions on the repository.
4. Add screenshots to `docs/images/` when ready (optional — app does not depend on them).
