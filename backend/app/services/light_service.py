from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from app.database.db import get_connection
from app.database.mongo import get_mongo_db
from app.models.collections import CollectionNames

# Light state and brightness
DEFAULT_LIGHT_STATE_OFF = "off"
DEFAULT_BRIGHTNESS_OFF = 0
DEFAULT_BRIGHTNESS_ON_PERCENT = 85
BRIGHTNESS_MIN = 0
BRIGHTNESS_MAX = 100

# History and pagination
HISTORY_PAGE_SIZE = 100
UNKNOWN_LEGACY_ID = 0  # fallback when a history document has no legacyId

# MongoDB sort order
MONGO_SORT_ASCENDING = 1
MONGO_SORT_DESCENDING = -1

# Schedule rules: use first rule when deriving schedule_on/schedule_off from Schedules collection
FIRST_SCHEDULE_RULE_INDEX = 0
DEFAULT_HOUR = 0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _datetime_to_iso(value: Any) -> str:
    """Turn MongoDB date or ISO string into ISO string."""
    if value is None:
        return _utc_now_iso()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class LightRepository(ABC):
    """
    Repository abstraction to allow a future SQLite -> MongoDB swap
    without changing route or business logic code.
    """

    @abstractmethod
    def get_or_create_light(self, restaurant_id: int) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update_light(
        self,
        restaurant_id: int,
        state: str,
        brightness: int,
        schedule_on: str | None = None,
        schedule_off: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def add_history(self, restaurant_id: int, action: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_history(self, restaurant_id: int | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    # New abstract methods for full schedule management
    @abstractmethod
    def save_full_schedule(self, restaurant_id: int, rules: list[dict[str, Any]]) -> dict[str, Any]:
        """Save day-specific schedule rules to Schedules collection"""
        raise NotImplementedError

    @abstractmethod
    def get_full_schedule(self, restaurant_id: int) -> dict[str, Any]:
        """Get day-specific schedule rules from Schedules collection"""
        raise NotImplementedError


class SQLiteLightRepository(LightRepository):
    """SQLite backend when MONGODB_URI is not set."""
    
    def get_or_create_light(self, restaurant_id: int) -> dict[str, Any]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM restaurant_lights WHERE restaurant_id = ?",
                (restaurant_id,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)

            now = _utc_now_iso()
            cursor.execute(
                """
                INSERT INTO restaurant_lights (
                    restaurant_id, state, brightness, schedule_on, schedule_off, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (restaurant_id, DEFAULT_LIGHT_STATE_OFF, DEFAULT_BRIGHTNESS_OFF, None, None, now),
            )
            return {
                "restaurant_id": restaurant_id,
                "state": DEFAULT_LIGHT_STATE_OFF,
                "brightness": DEFAULT_BRIGHTNESS_OFF,
                "schedule_on": None,
                "schedule_off": None,
                "last_updated": now,
            }

    def update_light(
        self,
        restaurant_id: int,
        state: str,
        brightness: int,
        schedule_on: str | None = None,
        schedule_off: str | None = None,
    ) -> dict[str, Any]:
        existing = self.get_or_create_light(restaurant_id)
        now = _utc_now_iso()
        next_schedule_on = existing["schedule_on"] if schedule_on is None else schedule_on
        next_schedule_off = (
            existing["schedule_off"] if schedule_off is None else schedule_off
        )

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE restaurant_lights
                SET state = ?, brightness = ?, schedule_on = ?, schedule_off = ?, last_updated = ?
                WHERE restaurant_id = ?
                """,
                (state, brightness, next_schedule_on, next_schedule_off, now, restaurant_id),
            )
            return {
                "restaurant_id": restaurant_id,
                "state": state,
                "brightness": brightness,
                "schedule_on": next_schedule_on,
                "schedule_off": next_schedule_off,
                "last_updated": now,
            }

    def add_history(self, restaurant_id: int, action: str) -> None:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO light_history (restaurant_id, action, timestamp)
                VALUES (?, ?, ?)
                """,
                (restaurant_id, action, _utc_now_iso()),
            )

    def get_history(self, restaurant_id: int | None = None) -> list[dict[str, Any]]:
        with get_connection() as conn:
            cursor = conn.cursor()
            if restaurant_id is None:
                cursor.execute(
                    "SELECT * FROM light_history ORDER BY timestamp DESC LIMIT ?",
                    (HISTORY_PAGE_SIZE,),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM light_history
                    WHERE restaurant_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (restaurant_id, HISTORY_PAGE_SIZE),
                )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
              
    def save_full_schedule(self, restaurant_id: int, rules: list[dict[str, Any]]) -> dict[str, Any]:
        """SQLite version - not implemented, return simple format"""
        return {"restaurant_id": restaurant_id, "rules": rules, "note": "SQLite does not support day-specific schedules"}

    def get_full_schedule(self, restaurant_id: int) -> dict[str, Any]:
        """SQLite version - return empty rules"""
        return {"restaurant_id": restaurant_id, "rules": []}



class MongoLightRepository(LightRepository):
    """
    SD_IoT MongoDB: Devices, light_history, Schedules, Time_Data, users.
    Field names match app.models.collections (DeviceDocument, LightHistoryDocument, etc.).
    """
    DEVICES = CollectionNames.DEVICES
    SCHEDULES = CollectionNames.SCHEDULES
    LIGHT_HISTORY = CollectionNames.LIGHT_HISTORY

    def __init__(self) -> None:
        self._db = get_mongo_db()

    def _device_for_restaurant_id(self, restaurant_id: int) -> dict[str, Any] | None:
        devices = self._db[self.DEVICES]
        device_doc = devices.find_one({"legacyId": restaurant_id})
        if device_doc is not None:
            return device_doc
        cursor = devices.find().sort("_id", MONGO_SORT_ASCENDING).skip(restaurant_id - 1).limit(1)
        return next(cursor, None)

    def _status_row_from_device(self, device: dict[str, Any], restaurant_id: int) -> dict[str, Any]:
        # Devices collection: lightState, brightness, scheduleOn, scheduleOff, lastUpdated
        state = device.get("lightState", DEFAULT_LIGHT_STATE_OFF)
        brightness = int(device.get("brightness", DEFAULT_BRIGHTNESS_OFF))
        schedule_on = device.get("scheduleOn")
        schedule_off = device.get("scheduleOff")
        if schedule_on is None or schedule_off is None:
            schedule_doc = self._schedule_for_device(device)
            if schedule_doc and schedule_doc.get("rules"):
                first_rule = schedule_doc["rules"][FIRST_SCHEDULE_RULE_INDEX]
                schedule_on = schedule_on or f"{first_rule.get('startHour', DEFAULT_HOUR):02d}:00"
                schedule_off = schedule_off or f"{first_rule.get('endHour', DEFAULT_HOUR):02d}:00"
        last_updated_raw = (
            device.get("lastUpdated")
            or device.get("updatedAt")
            or (device.get("status") or {}).get("lastSeen")
        )
        last_updated = _datetime_to_iso(last_updated_raw)
        return {
            "restaurant_id": restaurant_id,
            "state": state if state in ("on", "off") else DEFAULT_LIGHT_STATE_OFF,
            "brightness": max(BRIGHTNESS_MIN, min(BRIGHTNESS_MAX, brightness)),
            "schedule_on": schedule_on,
            "schedule_off": schedule_off,
            "last_updated": last_updated,
        }

    def _schedule_for_device(self, device: dict[str, Any]) -> dict[str, Any] | None:
        schedules = self._db[self.SCHEDULES]
        schedule_id = device.get("scheduleId")
        if schedule_id is not None:
            return schedules.find_one({"_id": schedule_id})
        device_id = device.get("_id")
        if device_id is not None:
            return schedules.find_one({"deviceId": device_id})
        return None

    def get_or_create_light(self, restaurant_id: int) -> dict[str, Any]:
        device = self._device_for_restaurant_id(restaurant_id)
        if device is None:
            return {
                "restaurant_id": restaurant_id,
                "state": DEFAULT_LIGHT_STATE_OFF,
                "brightness": DEFAULT_BRIGHTNESS_OFF,
                "schedule_on": None,
                "schedule_off": None,
                "last_updated": _utc_now_iso(),
            }
        return self._status_row_from_device(device, restaurant_id)

    def update_light(
        self,
        restaurant_id: int,
        state: str,
        brightness: int,
        schedule_on: str | None = None,
        schedule_off: str | None = None,
    ) -> dict[str, Any]:
        device = self._device_for_restaurant_id(restaurant_id)
        if device is None:
            return self.get_or_create_light(restaurant_id)
        devices = self._db[self.DEVICES]
        now = datetime.now(timezone.utc)
        update: dict[str, Any] = {
            "lightState": state,
            "brightness": brightness,
            "lastUpdated": now.isoformat(),
            "updatedAt": now,
        }
        if schedule_on is not None:
            update["scheduleOn"] = schedule_on
        if schedule_off is not None:
            update["scheduleOff"] = schedule_off
        devices.update_one({"_id": device["_id"]}, {"$set": update})
        return {
            "restaurant_id": restaurant_id,
            "state": state,
            "brightness": brightness,
            "schedule_on": schedule_on or device.get("scheduleOn"),
            "schedule_off": schedule_off or device.get("scheduleOff"),
            "last_updated": now.isoformat(),
        }

    def add_history(self, restaurant_id: int, action: str) -> None:
        # light_history collection: restaurantId, deviceId, action, timestamp, legacyId
        device = self._device_for_restaurant_id(restaurant_id)
        now = datetime.now(timezone.utc)
        history_entry: dict[str, Any] = {
            "restaurantId": device["restaurantId"] if device else str(restaurant_id),
            "action": action,
            "timestamp": now.isoformat(),
            "legacyId": restaurant_id,
        }
        if device:
            history_entry["deviceId"] = device["_id"]
        self._db[self.LIGHT_HISTORY].insert_one(history_entry)

    def get_history(self, restaurant_id: int | None = None) -> list[dict[str, Any]]:
        history_coll = self._db[self.LIGHT_HISTORY]
        if restaurant_id is not None:
            history_filter: dict[str, Any] = {"legacyId": restaurant_id}
        else:
            history_filter = {}
        cursor = history_coll.find(history_filter).sort(
            "timestamp", MONGO_SORT_DESCENDING
        ).limit(HISTORY_PAGE_SIZE)
        rows: list[dict[str, Any]] = []
        for index, history_doc in enumerate(cursor):
            event_timestamp = history_doc.get("timestamp")
            response_restaurant_id = history_doc.get("legacyId")
            if response_restaurant_id is None and restaurant_id is not None:
                response_restaurant_id = restaurant_id
            elif response_restaurant_id is None:
                response_restaurant_id = UNKNOWN_LEGACY_ID
            rows.append({
                "id": index + 1,
                "restaurant_id": response_restaurant_id,
                "action": history_doc["action"],
                "timestamp": _datetime_to_iso(event_timestamp) if event_timestamp else "",
            })
        return rows

    def save_full_schedule(self, restaurant_id: int, rules: list[dict[str, Any]]) -> dict[str, Any]:
        """Save day-specific schedule rules to Schedules collection - one rule per day"""
        # First get the device
        device = self._device_for_restaurant_id(restaurant_id)
        if not device:
            raise ValueError(f"Device with legacyId {restaurant_id} not found")
        
        schedules = self._db[self.SCHEDULES]
        now = datetime.now(timezone.utc)
        
        # Format each rule individually - one per day
        formatted_rules = []
        for rule in rules:
            # Each rule should have exactly one day (from your frontend)
            formatted_rule = {
                "days": rule.get("days", []),  # Should be a single-day array like ["MON"]
                "startHour": int(rule.get("startTime", "00:00").split(":")[0]),
                "endHour": int(rule.get("endTime", "00:00").split(":")[0]),
                "startMinute": int(rule.get("startTime", "00:00").split(":")[1]),
                "endMinute": int(rule.get("endTime", "00:00").split(":")[1]),
                "action": "ON",
                "enabled": rule.get("enabled", True)
            }
            formatted_rules.append(formatted_rule)
        
        # Check if schedule already exists
        existing = schedules.find_one({"deviceId": device["_id"]})
        
        schedule_data = {
            "deviceId": device["_id"],
            "restaurantId": device.get("restaurantId"),
            "restaurant": device.get("restaurant"),
            "rules": formatted_rules,
            "updatedAt": now
        }
        
        if existing:
            schedules.update_one({"_id": existing["_id"]}, {"$set": schedule_data})
            schedule_data["_id"] = str(existing["_id"])
        else:
            schedule_data["createdAt"] = now
            result = schedules.insert_one(schedule_data)
            schedule_data["_id"] = str(result.inserted_id)
        
        # Add to history
        self.add_history(restaurant_id, f"schedule_updated")
        
        # Convert back to response format
        return self.get_full_schedule(restaurant_id)

    def get_full_schedule(self, restaurant_id: int) -> dict[str, Any]:
        """Get day-specific schedule rules from Schedules collection"""
        device = self._device_for_restaurant_id(restaurant_id)
        if not device:
            return {"deviceId": None, "rules": []}
        
        schedules = self._db[self.SCHEDULES]
        schedule = schedules.find_one({"deviceId": device["_id"]})
        
        if not schedule:
            return {
                "deviceId": device["_id"],
                "restaurantId": device.get("restaurantId"),
                "rules": []
            }
        
        # Convert from storage format to response format - keep individual days
        rules_response = []
        for rule in schedule.get("rules", []):
            start_time = f"{rule.get('startHour', 0):02d}:{rule.get('startMinute', 0):02d}"
            end_time = f"{rule.get('endHour', 0):02d}:{rule.get('endMinute', 0):02d}"
            rules_response.append({
                "days": rule.get("days", []),  # Keep the days array
                "startTime": start_time,
                "endTime": end_time,
                "enabled": rule.get("enabled", True)
            })
        
        return {
            "deviceId": schedule["deviceId"],
            "restaurantId": schedule.get("restaurantId"),
            "rules": rules_response,
            "createdAt": _datetime_to_iso(schedule.get("createdAt")),
            "updatedAt": _datetime_to_iso(schedule.get("updatedAt"))
        }


class LightService:
    def __init__(self, repository: LightRepository) -> None:
        self.repository = repository

    def get_status(self, restaurant_id: int) -> dict[str, Any]:
        row = self.repository.get_or_create_light(restaurant_id)
        return self._to_status_response(row)

    def toggle_light(self, restaurant_id: int) -> dict[str, Any]:
        current = self.repository.get_or_create_light(restaurant_id)
        if current["state"] == DEFAULT_LIGHT_STATE_OFF:
            next_state = "on"
            next_brightness = (
                current["brightness"]
                if current["brightness"] > BRIGHTNESS_MIN
                else DEFAULT_BRIGHTNESS_ON_PERCENT
            )
            action = "toggle_on"
        else:
            next_state = DEFAULT_LIGHT_STATE_OFF
            next_brightness = DEFAULT_BRIGHTNESS_OFF
            action = "toggle_off"

        updated = self.repository.update_light(
            restaurant_id=restaurant_id,
            state=next_state,
            brightness=next_brightness,
        )
        self.repository.add_history(restaurant_id, action)
        return self._to_status_response(updated)

    def schedule_light(
        self, restaurant_id: int, schedule_on: str, schedule_off: str
    ) -> dict[str, Any]:
        current = self.repository.get_or_create_light(restaurant_id)
        updated = self.repository.update_light(
            restaurant_id=restaurant_id,
            state=current["state"],
            brightness=current["brightness"],
            schedule_on=schedule_on,
            schedule_off=schedule_off,
        )
        self.repository.add_history(
            restaurant_id, f"schedule_set_{schedule_on}_{schedule_off}"
        )
        return self._to_status_response(updated)

    # New methods for full schedule management
    def set_full_schedule(self, restaurant_id: int, rules: list[dict[str, Any]]) -> dict[str, Any]:
        """Save day-specific schedule rules"""
        return self.repository.save_full_schedule(restaurant_id, rules)

    def get_full_schedule(self, restaurant_id: int) -> dict[str, Any]:
        """Get day-specific schedule rules"""
        return self.repository.get_full_schedule(restaurant_id)

    def get_history(self, restaurant_id: int | None = None) -> list[dict[str, Any]]:
        rows = self.repository.get_history(restaurant_id)
        return [
            {
                "id": row["id"],
                "restaurantId": row["restaurant_id"],
                "action": row["action"],
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]

    @staticmethod
    def _to_status_response(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "restaurantId": row["restaurant_id"],
            "state": row["state"],
            "brightness": row["brightness"],
            "lastUpdated": row["last_updated"],
        }
