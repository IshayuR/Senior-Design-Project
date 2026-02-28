from datetime import datetime
from typing import Literal, List, Optional

from pydantic import BaseModel, Field


class ToggleLightRequest(BaseModel):
    restaurantId: int
    action: Literal["toggle"]


class DayScheduleRule(BaseModel):
    """One rule for a specific day or set of days"""
    days: List[str] = Field(..., description="e.g. ['MON', 'TUES', 'WED']")
    startTime: str = Field(..., description="HH:MM (24h) start time")
    endTime: str = Field(..., description="HH:MM (24h) end time")
    enabled: bool = Field(True, description="Whether this rule is active")


class FullScheduleRequest(BaseModel):
    """Complete schedule with day-specific rules"""
    restaurantId: int
    rules: List[DayScheduleRule] = Field(..., description="Schedule rules for each day")


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


class FullScheduleResponse(BaseModel):
    """Response for getting full schedule"""
    deviceId: Optional[str] = None
    rules: List[DayScheduleRule] = Field(default_factory=list)
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
