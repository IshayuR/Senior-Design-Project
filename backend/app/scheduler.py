"""
Built-in cron scheduler for the backend.

Every minute, checks today's effective schedule (custom date overrides
weekly) and publishes MQTT commands when the current time matches a
schedule's start or stop time.
"""

from __future__ import annotations

import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler

from app.mqtt_bridge import sync_device_schedule

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_last_sync_key: str | None = None

RESTAURANT_ID = 1


def _sync_today_schedule() -> None:
    """Push today's schedule to the physical device when the effective date changes."""
    global _last_sync_key
    today_iso = date.today().isoformat()
    if _last_sync_key == today_iso:
        return
    try:
        payload = sync_device_schedule(RESTAURANT_ID)
        if payload is not None:
            _last_sync_key = today_iso
            logger.info("Scheduler: synced today's device schedule")
    except Exception as e:
        logger.error("Scheduler: sync failed – %s", e)


def start_scheduler() -> None:
    """Start the background cron scheduler (fires every minute)."""
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _sync_today_schedule,
        trigger="cron",
        minute="*",
        id="sync_light_schedule",
    )
    _scheduler.start()
    _sync_today_schedule()
    logger.info("Scheduler: started (syncing every minute)")


def stop_scheduler() -> None:
    """Stop the background scheduler."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler: stopped")
