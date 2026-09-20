"""
APScheduler-based scheduler for the daily 05:00 IST pipeline run.

On startup:
- If it's after 05:00 IST and today's run is missing, it runs once immediately (catch-up).
- Then schedules the cron job for future days.

Plain-cron alternative:
  0 5 * * *   TZ=Asia/Kolkata python apix/scripts/run_once.py
  (05:00 IST = 23:30 UTC the previous calendar day)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from apix.config import load_config
from apix.db import get_connection, get_run_for_date, init_db
from apix.pipeline import run

logger = logging.getLogger(__name__)

_IST = pytz.timezone("Asia/Kolkata")


def _should_catch_up() -> bool:
    """Return True if it's past 05:00 IST and today's run hasn't happened."""
    now_ist = datetime.now(_IST)
    if now_ist.hour < 5:
        return False
    today = now_ist.date()
    init_db()
    with get_connection() as con:
        existing = get_run_for_date(con, today)
    return existing is None


def _daily_job() -> None:
    cfg = load_config()
    from datetime import date as date_type
    today = datetime.now(_IST).date()
    logger.info("Scheduler: starting daily run for %s", today)
    try:
        result = run(today, cfg=cfg)
        logger.info("Scheduler: run complete – %s", result)
    except Exception as exc:
        logger.error("Scheduler: run failed – %s", exc, exc_info=True)


def start_scheduler() -> BackgroundScheduler:
    """
    Create, configure and start the APScheduler instance.

    Returns the running scheduler so the caller can shut it down.
    """
    cfg = load_config()

    if _should_catch_up():
        logger.info("Catch-up: running missed 05:00 IST job now")
        _daily_job()

    scheduler = BackgroundScheduler(timezone=_IST)
    scheduler.add_job(
        _daily_job,
        CronTrigger(
            hour=cfg.schedule.hour,
            minute=cfg.schedule.minute,
            timezone=_IST,
        ),
        id="apix_daily",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started: daily job at %02d:%02d IST",
        cfg.schedule.hour,
        cfg.schedule.minute,
    )
    return scheduler
