"""
SD_IoT MongoDB schema: five collections (Devices, light_history, Schedules, Time_Data, users).
Use these for validation, serialization, and as the source of field names/metadata.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# Hour bounds for schedule rules (24h)
HOUR_MIN = 0
HOUR_MAX = 23
# Brightness percent bounds
BRIGHTNESS_PERCENT_MIN = 0
BRIGHTNESS_PERCENT_MAX = 100


# ---------------------------------------------------------------------------
# Collection 1: Devices
# ---------------------------------------------------------------------------

class DeviceAddress(BaseModel):
    """Address sub-document on Devices."""
    street: str = Field(..., description="Street address")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State code")
    zip: str = Field(..., description="ZIP code")


class DeviceContact(BaseModel):
    """Contact sub-document on Devices."""
    manager: str = Field(..., description="Manager email")
    phone: str = Field(..., description="Phone number")


class DeviceInfo(BaseModel):
    """Device hardware/firmware info sub-document on Devices."""
    model: str = Field(..., description="Device model e.g. ESP32")
    firmware: str = Field(..., description="Firmware version")
    installationDate: datetime = Field(..., description="When the device was installed")


class LastReading(BaseModel):
    """Last power reading in status.lastReading. Aliases V, I, P match MongoDB."""
    model_config = {"populate_by_name": True}

    voltage: float = Field(..., alias="V", description="Voltage")
    current: float = Field(..., alias="I", description="Current")
    power: float = Field(..., alias="P", description="Power")


class DeviceStatus(BaseModel):
    """Status sub-document on Devices."""
    lastSeen: datetime = Field(..., description="Last time device reported in")
    isOnline: bool = Field(..., description="Whether device is currently online")
    lastUptime: int | None = Field(None, description="Last reported uptime in seconds")
    lastReading: LastReading | None = Field(None, description="Last V/I/P reading")


class DeviceDocument(BaseModel):
    """
    Devices collection (SD_IoT). Restaurant/device information with light control fields.
    """
    model_config = {"populate_by_name": True, "extra": "allow"}

    _id: str = Field(..., alias="_id", description="Device ID e.g. ESP32_MCD_DARIEN_001")
    restaurant: str = Field(..., description="Restaurant display name")
    restaurantId: str = Field(..., description="Restaurant business ID e.g. mcd_1234")
    location: str = Field(..., description="Location description")
    address: DeviceAddress = Field(..., description="Address object")
    contact: DeviceContact = Field(..., description="Contact info")
    device: DeviceInfo = Field(..., description="Device model/firmware info")
    status: DeviceStatus = Field(..., description="Online status and last reading")
    scheduleId: Any | None = Field(None, description="Reference to Schedules._id (ObjectId)")
    createdAt: datetime = Field(..., description="Creation timestamp (ISO)")
    updatedAt: datetime = Field(..., description="Last update timestamp (ISO)")
    ownerEmail: str = Field(..., description="Owner email (references users)")

    # Light control fields
    lightState: Literal["on", "off"] | None = Field(None, description="Light on/off")
    brightness: int | None = Field(
        None, ge=BRIGHTNESS_PERCENT_MIN, le=BRIGHTNESS_PERCENT_MAX,
        description="Brightness 0-100"
    )
    scheduleOn: str | None = Field(None, description="Schedule on time 'HH:MM' or null")
    scheduleOff: str | None = Field(None, description="Schedule off time 'HH:MM' or null")
    lastUpdated: str | datetime | None = Field(None, description="ISO timestamp of last light-state change")
    legacyId: int | None = Field(None, description="Integer 1-5; maps API restaurant_id to this device")


# ---------------------------------------------------------------------------
# Collection 2: Schedules
# ---------------------------------------------------------------------------

class ScheduleRule(BaseModel):
    """One rule in Schedules.rules array."""
    days: list[str] = Field(..., description="e.g. ['MON','TUES','WED','THURS','FRI']")
    startHour: int = Field(..., ge=HOUR_MIN, le=HOUR_MAX, description="Start hour (24h)")
    endHour: int = Field(..., ge=HOUR_MIN, le=HOUR_MAX, description="End hour (24h)")
    action: Literal["ON", "OFF"] = Field(..., description="ON or OFF")


class ScheduleDocument(BaseModel):
    """
    Schedules collection (SD_IoT). Detailed schedule rules per device.
    """
    model_config = {"populate_by_name": True, "extra": "allow"}

    _id: Any = Field(..., alias="_id", description="Schedule ObjectId")
    deviceId: str = Field(..., description="Device ID this schedule applies to")
    restaurant: str = Field(..., description="Restaurant name")
    restaurantId: str | None = Field(None, description="Restaurant business ID")
    name: str = Field(..., description="Schedule name e.g. Exterior Lights Schedule")
    enabled: bool = Field(..., description="Whether schedule is active")
    rules: list[ScheduleRule] = Field(..., description="List of day/hour rules")
    createdBy: str = Field(..., description="Creator email")
    createdAt: str | datetime = Field(..., description="Creation timestamp")
    updatedAt: str | datetime = Field(..., description="Last update timestamp")


# ---------------------------------------------------------------------------
# Collection 3: Time_Data
# ---------------------------------------------------------------------------

class TimeDataMetadata(BaseModel):
    """metadata sub-document on Time_Data."""
    deviceId: str = Field(..., description="Device that produced this reading")
    location: str = Field(..., description="Location description")
    restaurant: str = Field(..., description="Restaurant name")
    restaurantId: str = Field(..., description="Restaurant business ID")


class TimeDataMeasurements(BaseModel):
    """measurements sub-document on Time_Data. Aliases V, I, P match MongoDB."""
    model_config = {"populate_by_name": True}

    voltage: float = Field(..., alias="V", description="Voltage")
    current: float = Field(..., alias="I", description="Current")
    power: float = Field(..., alias="P", description="Power")
    uptime: int = Field(..., description="Device uptime in seconds")


class TimeDataDocument(BaseModel):
    """
    Time_Data collection (SD_IoT). Time-series sensor readings.
    """
    model_config = {"populate_by_name": True, "extra": "allow"}

    _id: Any = Field(..., alias="_id", description="Document ObjectId")
    timestamp: datetime = Field(..., description="Reading timestamp")
    metadata: TimeDataMetadata = Field(..., description="Device/location metadata")
    measurements: TimeDataMeasurements = Field(..., description="V, I, P, uptime")


# ---------------------------------------------------------------------------
# Collection 4: users
# ---------------------------------------------------------------------------

class UserDocument(BaseModel):
    """
    users collection (SD_IoT). User accounts and device access.
    """
    model_config = {"populate_by_name": True, "extra": "allow"}

    _id: str = Field(..., alias="_id", description="User ID (email)")
    email: str = Field(..., description="Email")
    name: str = Field(..., description="Display name")
    password: str = Field(..., description="Hashed password")
    role: str = Field(..., description="e.g. Admin")
    restaurants: list[str] = Field(default_factory=list, description="Device IDs user can access")
    createdAt: datetime = Field(..., description="Creation timestamp")
    updatedAt: datetime = Field(..., description="Last update timestamp")


# ---------------------------------------------------------------------------
# light_history (SD_IoT)
# ---------------------------------------------------------------------------

class LightHistoryDocument(BaseModel):
    """
    light_history collection (SD_IoT). Logs every light action.
    """
    model_config = {"populate_by_name": True, "extra": "allow"}

    _id: Any | None = Field(None, alias="_id")
    restaurantId: str = Field(..., description="Restaurant ID e.g. mcd_1234")
    deviceId: str | None = Field(None, description="Device _id (matches Devices._id)")
    action: str = Field(..., description="toggle_on, toggle_off, schedule_set")
    timestamp: str | datetime = Field(..., description="ISO timestamp of the event")
    legacyId: int | None = Field(None, description="Integer matching device legacyId (1-5)")


# ---------------------------------------------------------------------------
# Collection names (single source of truth)
# ---------------------------------------------------------------------------

class CollectionNames:
    """SD_IoT collection names."""
    DEVICES = "Devices"
    SCHEDULES = "Schedules"
    TIME_DATA = "Time_Data"
    USERS = "users"
    LIGHT_HISTORY = "light_history"
