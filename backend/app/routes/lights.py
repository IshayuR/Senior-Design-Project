import logging

from fastapi import APIRouter, HTTPException, Query, Request

from app.models.light import (
    LightHistoryItem,
    LightStatusResponse,
    ScheduleLightRequest,
    ToggleLightRequest,
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
