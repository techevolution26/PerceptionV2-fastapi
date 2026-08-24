# app/services/scheduler.py
"""
Runs the daily-digest job in-process via APScheduler.

Note for production: if you ever run more than one API replica, this will
fire once per replica (duplicate notifications). At that point move this to
a dedicated single-instance worker — a separate `worker` service in
docker-compose running just this scheduler, or Celery beat — rather than
inside every API pod. Fine as-is for a single-instance deployment.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.daily_digest import run_daily_digest

logger = logging.getLogger("scheduler")

# 08:00 Africa/Nairobi (EAT, UTC+3) — matches the original Laravel
# schedule's ->dailyAt('08:00') for the primary East-Africa-based audience.
_TRIGGER = CronTrigger(hour=8, minute=0, timezone="Africa/Nairobi")


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_digest, _TRIGGER, id="daily_digest", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler started — daily digest set for 08:00 Africa/Nairobi")
    return scheduler


def stop_scheduler(scheduler: AsyncIOScheduler) -> None:
    scheduler.shutdown(wait=False)
