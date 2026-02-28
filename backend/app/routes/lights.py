import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.light import (
    LightHistoryItem,
    LightStatusResponse,
    ScheduleLightRequest,
    ToggleLightRequest,
    FullScheduleRequest,
    FullScheduleResponse,
)
from app.services.light_service import LightService, MongoLightRepository, SQLiteLightRepository

router = APIRouter(prefix="/lights", tags=["lights"])

# Use MongoDB when MONGODB_URI is set; otherwise keep SQLite placeholder.
if os.getenv("MONGODB_URI"):
    service = LightService(repository=MongoLightRepository())
else:
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
    """Legacy endpoint: sets a simple schedule (same time every day)"""
    return service.schedule_light(
        restaurant_id=payload.restaurantId,
        schedule_on=payload.scheduleOn,
        schedule_off=payload.scheduleOff,
    )


@router.post("/schedule/full", response_model=FullScheduleResponse)
def set_full_schedule(payload: FullScheduleRequest) -> dict:
    """Save day-specific schedule rules to Schedules collection"""
    return service.set_full_schedule(
        restaurant_id=payload.restaurantId,
        rules=[rule.dict() for rule in payload.rules]
    )


@router.get("/schedule/full", response_model=FullScheduleResponse)
def get_full_schedule(restaurantId: int = Query(..., ge=1)) -> dict:
    """Get day-specific schedule rules from Schedules collection"""
    return service.get_full_schedule(restaurantId)


@router.get("/history", response_model=list[LightHistoryItem])
def get_light_history(restaurantId: int | None = Query(default=None, ge=1)) -> list[dict]:
    return service.get_history(restaurantId)
