import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request

from app.database.db import get_connection
from app.models.light import (
    CustomScheduleUpsertRequest,
    LightHistoryItem,
    LightStatusResponse,
    ScheduleLightRequest,
    TodayScheduleResponse,
    ToggleLightRequest,
    WeeklyScheduleUpsertRequest,
)
from app.services.light_service import LightService, SQLiteLightRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lights", tags=["lights"])
service = LightService(repository=SQLiteLightRepository())


@router.get("/status", response_model=LightStatusResponse)
def get_light_status(restaurantId: int = Query(..., ge=1)) -> dict:
    return service.get_status(restaurantId)


@router.post("/toggle", response_model=LightStatusResponse)
def toggle_light(payload: ToggleLightRequest, request: Request) -> dict:
    if payload.action != "toggle":
        raise HTTPException(status_code=400, detail="action must be 'toggle'")

    result = service.toggle_light(payload.restaurantId)

    mqtt_client = getattr(request.app.state, "mqtt", None)
    if mqtt_client and mqtt_client.is_connected:
        command = "on" if result["state"] == "on" else "off"
        try:
            mqtt_client.publish_command(command)
            logger.info("MQTT command '%s' sent to ESP32", command)
        except Exception as exc:
            logger.error("Failed to send MQTT command: %s", exc)
    else:
        logger.warning("MQTT not connected — toggle applied to DB only")

    return result


@router.post("/schedule", response_model=LightStatusResponse)
def schedule_light(payload: ScheduleLightRequest) -> dict:
    return service.schedule_light(
        restaurant_id=payload.restaurantId,
        schedule_on=payload.scheduleOn,
        schedule_off=payload.scheduleOff,
    )


@router.get("/history", response_model=list[LightHistoryItem])
def get_light_history(restaurantId: int | None = Query(default=None, ge=1)) -> list[dict]:
    return service.get_history(restaurantId)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/schedule/weekly")
def upsert_weekly_schedule(payload: WeeklyScheduleUpsertRequest) -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        for day in payload.days:
            cursor.execute(
                """
                INSERT INTO weekly_schedule (restaurant_id, day_of_week, enabled, start_time, stop_time, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(restaurant_id, day_of_week) DO UPDATE SET
                    enabled = excluded.enabled,
                    start_time = excluded.start_time,
                    stop_time = excluded.stop_time,
                    updated_at = excluded.updated_at
                """,
                (payload.restaurantId, day.dayOfWeek, int(day.enabled), day.start, day.stop, _utc_now_iso()),
            )
    return {"ok": True}


@router.post("/schedule/custom")
def upsert_custom_schedule(payload: CustomScheduleUpsertRequest) -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM custom_schedule WHERE restaurant_id = ?",
            (payload.restaurantId,),
        )
        for entry in payload.dates:
            cursor.execute(
                """
                INSERT INTO custom_schedule (restaurant_id, schedule_date, start_time, stop_time, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (payload.restaurantId, entry.schedule_date.isoformat(), entry.start, entry.stop, _utc_now_iso()),
            )
    return {"ok": True}


@router.get("/schedule/today", response_model=TodayScheduleResponse)
def get_today_schedule(restaurantId: int = Query(..., ge=1)) -> dict:
    """Return today's effective on/off schedule, with custom dates overriding weekly."""
    today = date.today()
    today_iso = today.isoformat()

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT start_time, stop_time FROM custom_schedule WHERE restaurant_id = ? AND schedule_date = ?",
            (restaurantId, today_iso),
        )
        custom_row = cursor.fetchone()
        if custom_row:
            return {
                "restaurantId": restaurantId,
                "scheduleOn": custom_row["start_time"],
                "scheduleOff": custom_row["stop_time"],
            }

        weekday = today.weekday()
        cursor.execute(
            "SELECT enabled, start_time, stop_time FROM weekly_schedule WHERE restaurant_id = ? AND day_of_week = ?",
            (restaurantId, weekday),
        )
        weekly_row = cursor.fetchone()
        if weekly_row and weekly_row["enabled"]:
            return {
                "restaurantId": restaurantId,
                "scheduleOn": weekly_row["start_time"],
                "scheduleOff": weekly_row["stop_time"],
            }

    return {"restaurantId": restaurantId, "scheduleOn": None, "scheduleOff": None}
