"""CLI entry point for AI Intelligence Observatory."""

from __future__ import annotations

import argparse

from ai_observatory.agents.weekly_trends import generate_weekly_report
from ai_observatory.crew import run_observatory_crew
from ai_observatory.database import init_db
from ai_observatory.diagnostics import log_startup_diagnostics
from ai_observatory.logging_setup import logger
from ai_observatory.reports.pdf_generator import generate_weekly_pdf
from ai_observatory.scheduler import start_scheduler


def main() -> None:
    log_startup_diagnostics()
    parser = argparse.ArgumentParser(description="AI Intelligence Observatory")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Generate today's executive briefing")
    run_parser.add_argument("--email", action="store_true", help="Send briefing via email")

    sub.add_parser("schedule", help="Start daily scheduler")
    sub.add_parser("init-db", help="Initialize SQLite database")
    sub.add_parser("weekly-report", help="Generate weekly trend report")
    sub.add_parser("weekly-pdf", help="Generate weekly executive PDF report")

    args = parser.parse_args()

    if args.command == "init-db":
        init_db()
        logger.info("Database initialized")
        return

    if args.command == "weekly-report":
        init_db()
        report = generate_weekly_report()
        logger.info("Weekly report generated", extra={"summary": report.get("executive_summary")})
        return

    if args.command == "weekly-pdf":
        init_db()
        pdf_path = generate_weekly_pdf()
        logger.info("Weekly PDF generated", extra={"path": str(pdf_path)})
        return

    if args.command == "schedule":
        start_scheduler()
        return

    if args.command == "run":
        result = run_observatory_crew(send_email=args.email)
        if result.get("success"):
            logger.info("Briefing run complete", extra=result)
        else:
            logger.error("Briefing run failed", extra=result)
            raise SystemExit(1)


if __name__ == "__main__":
    main()
