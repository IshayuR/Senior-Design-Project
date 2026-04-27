from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.database.db import get_connection
from app.mqtt_bridge import get_effective_schedule_window, sync_device_schedule
from app.models.light import (
    CustomScheduleUpsertRequest,
    CustomScheduleResponse,
    LightHistoryItem,
    LightStatusResponse,
    ScheduleLightRequest,
    TodayScheduleResponse,
    ToggleLightRequest,
    WeeklyScheduleResponse,
    WeeklyScheduleUpsertRequest,
)
from app.services.light_service import LightService, SQLiteLightRepository

router = APIRouter(prefix="/lights", tags=["lights"])
service = LightService(repository=SQLiteLightRepository())


@router.get("/status", response_model=LightStatusResponse)
def get_light_status(restaurantId: int = Query(..., ge=1)) -> dict:
    return service.get_status(restaurantId)


@router.post("/toggle", response_model=LightStatusResponse)
def toggle_light(payload: ToggleLightRequest) -> dict:
    if payload.action != "toggle":
        raise HTTPException(status_code=400, detail="action must be 'toggle'")

    return service.toggle_light(payload.restaurantId)


@router.post("/schedule", response_model=LightStatusResponse)
def schedule_light(payload: ScheduleLightRequest) -> dict:
    result = service.schedule_light(
        restaurant_id=payload.restaurantId,
        schedule_on=payload.scheduleOn,
        schedule_off=payload.scheduleOff,
    )
    sync_device_schedule(payload.restaurantId)
    return result


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
    sync_device_schedule(payload.restaurantId)
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
    sync_device_schedule(payload.restaurantId)
    return {"ok": True}


@router.get("/schedule/weekly", response_model=WeeklyScheduleResponse)
def get_weekly_schedule(restaurantId: int = Query(..., ge=1)) -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT day_of_week, enabled, start_time, stop_time
            FROM weekly_schedule
            WHERE restaurant_id = ?
            ORDER BY day_of_week ASC
            """,
            (restaurantId,),
        )
        rows = cursor.fetchall()

    return {
        "restaurantId": restaurantId,
        "days": [
            {
                "dayOfWeek": row["day_of_week"],
                "enabled": bool(row["enabled"]),
                "start": row["start_time"],
                "stop": row["stop_time"],
            }
            for row in rows
        ],
    }


@router.get("/schedule/custom", response_model=CustomScheduleResponse)
def get_custom_schedule(restaurantId: int = Query(..., ge=1)) -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT schedule_date, start_time, stop_time
            FROM custom_schedule
            WHERE restaurant_id = ?
            ORDER BY schedule_date ASC
            """,
            (restaurantId,),
        )
        rows = cursor.fetchall()

    return {
        "restaurantId": restaurantId,
        "dates": [
            {
                "date": row["schedule_date"],
                "start": row["start_time"],
                "stop": row["stop_time"],
            }
            for row in rows
        ],
    }


@router.get("/schedule/today", response_model=TodayScheduleResponse)
def get_today_schedule(restaurantId: int = Query(..., ge=1)) -> dict:
    """Return today's effective on/off schedule, with custom dates overriding weekly."""
    schedule_on, schedule_off = get_effective_schedule_window(restaurantId, date.today())
    return {"restaurantId": restaurantId, "scheduleOn": schedule_on, "scheduleOff": schedule_off}
