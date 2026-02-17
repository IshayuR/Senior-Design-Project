import os

from fastapi import APIRouter, HTTPException, Query

from app.models.light import (
    LightHistoryItem,
    LightStatusResponse,
    ScheduleLightRequest,
    ToggleLightRequest,
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
    return service.schedule_light(
        restaurant_id=payload.restaurantId,
        schedule_on=payload.scheduleOn,
        schedule_off=payload.scheduleOff,
    )


@router.get("/history", response_model=list[LightHistoryItem])
def get_light_history(restaurantId: int | None = Query(default=None, ge=1)) -> list[dict]:
    return service.get_history(restaurantId)
