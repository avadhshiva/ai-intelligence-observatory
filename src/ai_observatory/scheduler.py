"""Daily scheduler for morning briefings."""

from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from ai_observatory.config import settings
from ai_observatory.crew import run_observatory_crew
from ai_observatory.logging_setup import logger


def run_scheduled_briefing() -> None:
    logger.info("Scheduled briefing job started")
    result = run_observatory_crew(send_email=True)
    logger.info("Scheduled briefing job finished", extra={"result": result})


def start_scheduler() -> None:
    scheduler = BlockingScheduler(timezone=settings.schedule_timezone)
    trigger = CronTrigger(
        hour=settings.schedule_hour,
        minute=settings.schedule_minute,
        timezone=settings.schedule_timezone,
    )
    scheduler.add_job(
        run_scheduled_briefing,
        trigger=trigger,
        id="daily_ai_briefing",
        replace_existing=True,
    )
    logger.info(
        "Scheduler started",
        extra={
            "hour": settings.schedule_hour,
            "minute": settings.schedule_minute,
            "timezone": settings.schedule_timezone,
        },
    )
    scheduler.start()
