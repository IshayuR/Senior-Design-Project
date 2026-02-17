from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ToggleLightRequest(BaseModel):
    restaurantId: int
    action: Literal["toggle"]


class ScheduleLightRequest(BaseModel):
    restaurantId: int
    scheduleOn: str = Field(..., description="HH:MM (24h) schedule on time")
    scheduleOff: str = Field(..., description="HH:MM (24h) schedule off time")


class LightStatusResponse(BaseModel):
    restaurantId: int
    state: Literal["on", "off"]
    brightness: int
    lastUpdated: datetime


class LightHistoryItem(BaseModel):
    id: int
    restaurantId: int
    action: str
    timestamp: datetime
