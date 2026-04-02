from datetime import date, datetime
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
    scheduleOn: str | None = None
    scheduleOff: str | None = None


class LightHistoryItem(BaseModel):
    id: int
    restaurantId: int
    action: str
    timestamp: datetime


class WeeklyDaySchedule(BaseModel):
    dayOfWeek: int = Field(..., ge=0, le=6, description="0=Monday ... 6=Sunday (Python weekday())")
    enabled: bool
    start: str = Field(..., description="HH:MM (24h)")
    stop: str = Field(..., description="HH:MM (24h)")


class WeeklyScheduleUpsertRequest(BaseModel):
    restaurantId: int
    days: list[WeeklyDaySchedule]


class CustomDateEntry(BaseModel):
    schedule_date: date = Field(..., alias="date", description="Calendar date (YYYY-MM-DD)")
    start: str = Field(..., description="HH:MM (24h)")
    stop: str = Field(..., description="HH:MM (24h)")


class CustomScheduleUpsertRequest(BaseModel):
    restaurantId: int
    dates: list[CustomDateEntry]


class TodayScheduleResponse(BaseModel):
    restaurantId: int
    scheduleOn: str | None = None
    scheduleOff: str | None = None
