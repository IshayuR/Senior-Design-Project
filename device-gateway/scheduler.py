"""Cron-style scheduler: runs schedule-check job to apply light on/off from backend."""
from datetime import datetime

import requests
from apscheduler.schedulers.background import BackgroundScheduler

from config import BACKEND_URL, RESTAURANT_ID, SCHEDULER_CRON_HOUR, SCHEDULER_CRON_MINUTE


def _current_time_str() -> str:
    """Current local time as HH:MM (24h)."""
    return datetime.now().strftime("%H:%M")


def _apply_schedule_job() -> None:
    """Fetch light schedule from backend; if current time matches schedule_on/off, publish to MQTT."""
    try:
        r = requests.get(
            f"{BACKEND_URL}/lights/status",
            params={"restaurantId": RESTAURANT_ID},
            timeout=5,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print("Scheduler: failed to fetch schedule:", e)
        return

    schedule_on = data.get("scheduleOn")
    schedule_off = data.get("scheduleOff")
    if not schedule_on and not schedule_off:
        return

    now = _current_time_str()
    try:
        from mqtt_client import publish_light_state

        if schedule_on and now == schedule_on:
            publish_light_state("on")
            print("Scheduler: applied schedule_on at", now)
        elif schedule_off and now == schedule_off:
            publish_light_state("off")
            print("Scheduler: applied schedule_off at", now)
    except Exception as e:
        print("Scheduler: MQTT publish failed:", e)


_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    """Start the background scheduler with cron trigger (default: every minute)."""
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    # Cron: default "* * * * *" = every minute; override via SCHEDULER_CRON_* env
    _scheduler.add_job(
        _apply_schedule_job,
        trigger="cron",
        minute=SCHEDULER_CRON_MINUTE,
        hour=SCHEDULER_CRON_HOUR,
        id="apply_light_schedule",
    )
    _scheduler.start()
    print("Scheduler: cron job started (light schedule)")


def stop_scheduler() -> None:
    """Stop the background scheduler (e.g. on app shutdown)."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        print("Scheduler: stopped")
