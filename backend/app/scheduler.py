"""
Built-in cron scheduler for the backend.

Every minute, checks today's effective schedule (custom date overrides
weekly) and publishes MQTT commands when the current time matches a
schedule's start or stop time.
"""

from __future__ import annotations

import logging
from datetime import date, datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.database.db import get_connection
from app.mqtt_bridge import publish_light_command

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

RESTAURANT_ID = 1


def _check_schedule() -> None:
    """Fetch today's schedule from SQLite; publish MQTT if current time matches."""
    now_hhmm = datetime.now().strftime("%H:%M")
    today = date.today()
    today_iso = today.isoformat()

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT start_time, stop_time FROM custom_schedule "
                "WHERE restaurant_id = ? AND schedule_date = ?",
                (RESTAURANT_ID, today_iso),
            )
            row = cursor.fetchone()

            if not row:
                weekday = today.weekday()
                cursor.execute(
                    "SELECT start_time, stop_time FROM weekly_schedule "
                    "WHERE restaurant_id = ? AND day_of_week = ? AND enabled = 1",
                    (RESTAURANT_ID, weekday),
                )
                row = cursor.fetchone()

            if not row:
                return

            schedule_on = row["start_time"]
            schedule_off = row["stop_time"]

            if schedule_on and now_hhmm == schedule_on:
                publish_light_command("on")
                logger.info("Scheduler: applied schedule_on at %s", now_hhmm)
            elif schedule_off and now_hhmm == schedule_off:
                publish_light_command("off")
                logger.info("Scheduler: applied schedule_off at %s", now_hhmm)
    except Exception as e:
        logger.error("Scheduler: check failed – %s", e)


def start_scheduler() -> None:
    """Start the background cron scheduler (fires every minute)."""
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _check_schedule,
        trigger="cron",
        minute="*",
        id="check_light_schedule",
    )
    _scheduler.start()
    logger.info("Scheduler: started (checking every minute)")


def stop_scheduler() -> None:
    """Stop the background scheduler."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler: stopped")
