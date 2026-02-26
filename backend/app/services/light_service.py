from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from app.database.db import get_connection


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


class SQLiteLightRepository(LightRepository):
    # MongoDB migration point:
    # add a MongoLightRepository implementing LightRepository,
    # then swap dependency wiring in routes/main without changing service logic.
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
                (restaurant_id, "off", 0, None, None, now),
            )
            return {
                "restaurant_id": restaurant_id,
                "state": "off",
                "brightness": 0,
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
                    "SELECT * FROM light_history ORDER BY timestamp DESC LIMIT 100"
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM light_history
                    WHERE restaurant_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 100
                    """,
                    (restaurant_id,),
                )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]


class LightService:
    def __init__(self, repository: LightRepository) -> None:
        self.repository = repository

    def get_status(self, restaurant_id: int) -> dict[str, Any]:
        row = self.repository.get_or_create_light(restaurant_id)
        return self._to_status_response(row)

    def toggle_light(self, restaurant_id: int) -> dict[str, Any]:
        current = self.repository.get_or_create_light(restaurant_id)
        if current["state"] == "off":
            next_state = "on"
            next_brightness = current["brightness"] if current["brightness"] > 0 else 85
            action = "toggle_on"
        else:
            next_state = "off"
            next_brightness = 0
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
