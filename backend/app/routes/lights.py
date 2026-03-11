from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query

from app.database.mongo import get_schedule_collection
from app.models.light import (
    CustomScheduleUpsertRequest,
    CustomDateEntry,
    LightHistoryItem,
    LightStatusResponse,
    ScheduleLightRequest,
    TodayScheduleResponse,
    ToggleLightRequest,
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
    return service.schedule_light(
        restaurant_id=payload.restaurantId,
        schedule_on=payload.scheduleOn,
        schedule_off=payload.scheduleOff,
    )


@router.get("/history", response_model=list[LightHistoryItem])
def get_light_history(restaurantId: int | None = Query(default=None, ge=1)) -> list[dict]:
    return service.get_history(restaurantId)


@router.post("/schedule/weekly")
def upsert_weekly_schedule(payload: WeeklyScheduleUpsertRequest) -> dict:
    col = get_schedule_collection()
    # Store one document per (restaurantId, dayOfWeek)
    for day in payload.days:
        col.update_one(
            {
                "restaurantId": payload.restaurantId,
                "kind": "weekly",
                "dayOfWeek": day.dayOfWeek,
            },
            {
                "$set": {
                    "enabled": day.enabled,
                    "start": day.start,
                    "stop": day.stop,
                    "updatedAt": datetime.utcnow(),
                }
            },
            upsert=True,
        )
    return {"ok": True}


@router.post("/schedule/custom")
def upsert_custom_schedule(payload: CustomScheduleUpsertRequest) -> dict:
    col = get_schedule_collection()
    # Remove any existing custom entries for this restaurant and re-insert
    col.delete_many({"restaurantId": payload.restaurantId, "kind": "custom"})
    docs: list[dict] = []
    for entry in payload.dates:
        docs.append(
            {
                "restaurantId": payload.restaurantId,
                "kind": "custom",
                "date": entry.schedule_date.isoformat(),
                "start": entry.start,
                "stop": entry.stop,
                "updatedAt": datetime.utcnow(),
            }
        )
    if docs:
        col.insert_many(docs)
    return {"ok": True}


@router.get("/schedule/today", response_model=TodayScheduleResponse)
def get_today_schedule(restaurantId: int = Query(..., ge=1)) -> dict:
    """Return today's effective on/off schedule, with custom dates overriding weekly."""
    col = get_schedule_collection()
    today = date.today()
    today_iso = today.isoformat()

    # 1) Custom override for today (highest priority)
    custom_doc = col.find_one(
        {"restaurantId": restaurantId, "kind": "custom", "date": today_iso}
    )
    if custom_doc:
        return {
            "restaurantId": restaurantId,
            "scheduleOn": custom_doc.get("start"),
            "scheduleOff": custom_doc.get("stop"),
        }

    # 2) Weekly schedule for today's weekday (0=Monday..6=Sunday)
    weekday = today.weekday()
    weekly_doc = col.find_one(
        {
            "restaurantId": restaurantId,
            "kind": "weekly",
            "dayOfWeek": weekday,
        }
    )
    if weekly_doc and weekly_doc.get("enabled", False):
        return {
            "restaurantId": restaurantId,
            "scheduleOn": weekly_doc.get("start"),
            "scheduleOff": weekly_doc.get("stop"),
        }

    # 3) No schedule
    return {"restaurantId": restaurantId, "scheduleOn": None, "scheduleOff": None}
