# Deployment Guide — AI Intelligence Observatory

This guide covers local setup, environment configuration, GitHub Actions automation, and troubleshooting.

## Local Deployment

### Prerequisites

- Python 3.10+ (3.11 recommended)
- Git
- OpenAI API key (for CrewAI pipeline)
- Gmail SMTP app password (for email delivery)
- NewsAPI key (optional — RSS feeds work without it)

### Virtual Environment Setup

```powershell
git clone https://github.com/YOUR_ORG/ai-intelligence-observatory.git
cd ai-intelligence-observatory

python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows
# source .venv/bin/activate         # macOS/Linux

python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .
```

### Configuration

```powershell
copy .env.example .env
copy config\user_profile.example.json config\user_profile.json
```

Edit `.env` with your credentials. Edit `config/user_profile.json` for personal relevance scoring.

### Verify Installation

```powershell
python scripts/health_check.py
pytest tests/ -q
python -m ai_observatory init-db
```

### Run Locally

```powershell
# Generate today's briefing (deterministic if USE_LLM=false)
python -m ai_observatory run

# Generate and email briefing
python -m ai_observatory run --email

# Launch dashboard
streamlit run dashboard/app.py

# Weekly report / PDF
python -m ai_observatory weekly-report
python -m ai_observatory weekly-pdf
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | For CrewAI | OpenAI API key |
| `OPENAI_MODEL` | No | Default: `gpt-4o-mini` |
| `USE_LLM` | No | Default: `true` |
| `NEWSAPI_KEY` | No | NewsAPI key for supplemental collection |
| `DATABASE_URL` | No | Default: `sqlite:///./data/observatory.db` |
| `SMTP_HOST` | For email | Default: `smtp.gmail.com` |
| `SMTP_PORT` | For email | Default: `587` |
| `SMTP_USER` | For email | SMTP username |
| `SMTP_PASSWORD` | For email | Gmail app password |
| `EMAIL_FROM` | For email | Sender address |
| `EMAIL_RECIPIENTS` | For email | Comma-separated or JSON list |
| `LOG_LEVEL` | No | Default: `INFO` |

See `.env.example` for the full list including scheduler and collection settings.

## GitHub Actions Setup

### Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `.github/workflows/tests.yml` | push, pull_request | pytest + health check |
| `.github/workflows/daily-briefing.yml` | cron 06:00 IST, manual | Daily briefing + email |

Daily schedule: **06:00 IST** = **00:30 UTC** (`cron: "30 0 * * *"`).

### Required GitHub Secrets

Configure under **Settings → Secrets and variables → Actions**:

| Secret | Purpose |
|--------|---------|
| `OPENAI_API_KEY` | CrewAI agent reasoning |
| `NEWSAPI_KEY` | NewsAPI collection (optional but recommended) |
| `SMTP_HOST` | Mail server hostname |
| `SMTP_PORT` | Mail server port (e.g. `587`) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password / app password |
| `EMAIL_FROM` | Sender email address |
| `EMAIL_RECIPIENTS` | Recipient list (comma-separated) |

### Optional Repository Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_MODEL` | `gpt-4o-mini` | Override model in daily workflow |

### Enabling Daily Automation

1. Push repository to GitHub.
2. Add all secrets listed above.
3. Enable Actions in repository settings.
4. Trigger manually via **Actions → Daily Briefing → Run workflow** to validate.
5. Confirm logs artifact and email delivery.

### CI Artifacts

- `daily-briefing-logs-<run_id>` — `logs/` directory (14-day retention)
- `observatory-db-<run_id>` — SQLite database after successful run (7-day retention)

## Troubleshooting

### Health check fails on imports

```powershell
pip install -r requirements-dev.txt
pip install -e .
```

### CrewAI parse failures / fallback used

Check **Dashboard → CrewAI Diagnostics** or `logs/raw_crewai_output.json`. The JSON repair pipeline logs explicit failure reasons.

### Email not sending

- Verify Gmail app password (not account password).
- Confirm `EMAIL_RECIPIENTS` is set.
- Run `python scripts/health_check.py` and review SMTP warnings.

### No stories collected

- RSS feeds may be temporarily unavailable — check logs.
- Add `NEWSAPI_KEY` for supplemental coverage.

### Dashboard won't start

```powershell
python scripts/health_check.py
streamlit run dashboard/app.py
```

### GitHub Actions daily workflow fails

- Verify all secrets are configured.
- Check workflow logs artifact for `logs/raw_crewai_output.json`.
- Ensure `config/user_profile.example.json` exists (workflow copies it automatically).

### Database locked / permission errors

Ensure `data/` directory is writable. On CI, the database is ephemeral per runner.

## Production Notes

- SQLite is suitable for single-runner automation; use a managed database for multi-instance deployments.
- Store secrets only in `.env` (local) or GitHub Secrets (CI).
- Never commit `config/user_profile.json` with personal data.
