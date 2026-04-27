"""
MQTT bridge – connects the FastAPI backend to AWS IoT Core.

Manages a persistent IoTMQTTClient and exposes a simple publish function
that the service layer calls when light state changes.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

# Resolve cert paths relative to project root before importing the client
for _var in ("AWS_IOT_CA_CERT", "AWS_IOT_BACKEND_CERT", "AWS_IOT_BACKEND_KEY"):
    _val = os.getenv(_var, "")
    if _val and not os.path.isabs(_val):
        os.environ[_var] = str(PROJECT_ROOT / _val)

from aws.device_protocol import snapshot_from_message
from aws.mqtt_client import IoTMQTTClient  # noqa: E402

from app.database.db import get_connection

logger = logging.getLogger(__name__)

_client: IoTMQTTClient | None = None
RESTAURANT_ID = 1


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_effective_schedule_window(
    restaurant_id: int,
    target_date: date | None = None,
) -> tuple[str | None, str | None]:
    schedule_date = target_date or date.today()
    schedule_date_iso = schedule_date.isoformat()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT start_time, stop_time
            FROM custom_schedule
            WHERE restaurant_id = ? AND schedule_date = ?
            """,
            (restaurant_id, schedule_date_iso),
        )
        custom_row = cursor.fetchone()
        if custom_row:
            return custom_row["start_time"], custom_row["stop_time"]

        cursor.execute(
            """
            SELECT enabled, start_time, stop_time
            FROM weekly_schedule
            WHERE restaurant_id = ? AND day_of_week = ?
            """,
            (restaurant_id, schedule_date.weekday()),
        )
        weekly_row = cursor.fetchone()
        if weekly_row and weekly_row["enabled"]:
            return weekly_row["start_time"], weekly_row["stop_time"]

    return None, None


def _update_device_snapshot(snapshot: dict[str, Any]) -> None:
    next_state = snapshot.get("state")
    next_mode = snapshot.get("mode")
    raw_status = snapshot.get("status")
    device_ip = snapshot.get("ip")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT state, brightness, schedule_on, schedule_off, device_status, device_mode, device_ip
            FROM restaurant_lights
            WHERE restaurant_id = ?
            """,
            (RESTAURANT_ID,),
        )
        row = cursor.fetchone()

        previous_state = row["state"] if row else "off"
        current_brightness = row["brightness"] if row else 0
        schedule_on = row["schedule_on"] if row else None
        schedule_off = row["schedule_off"] if row else None
        previous_status = row["device_status"] if row else None
        previous_mode = row["device_mode"] if row else None
        previous_ip = row["device_ip"] if row else None

        if next_state is None:
            next_state = previous_state

        next_brightness = (
            current_brightness if next_state == "on" and current_brightness > 0 else (85 if next_state == "on" else 0)
        )
        next_status = raw_status if raw_status is not None else previous_status
        resolved_mode = next_mode if next_mode is not None else previous_mode
        resolved_ip = device_ip if device_ip is not None else previous_ip

        cursor.execute(
            """
            INSERT INTO restaurant_lights (
                restaurant_id, state, brightness, schedule_on, schedule_off, device_mode,
                device_status, device_ip, last_seen_at, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(restaurant_id) DO UPDATE SET
                state = excluded.state,
                brightness = excluded.brightness,
                schedule_on = excluded.schedule_on,
                schedule_off = excluded.schedule_off,
                device_mode = excluded.device_mode,
                device_status = excluded.device_status,
                device_ip = excluded.device_ip,
                last_seen_at = excluded.last_seen_at,
                last_updated = excluded.last_updated
            """,
            (
                RESTAURANT_ID,
                next_state,
                next_brightness,
                schedule_on,
                schedule_off,
                resolved_mode,
                next_status,
                resolved_ip,
                _utc_now_iso(),
                _utc_now_iso(),
            ),
        )

        if previous_state != next_state or previous_status != next_status:
            cursor.execute(
                """
                INSERT INTO light_history (restaurant_id, action, timestamp)
                VALUES (?, ?, ?)
                """,
                (
                    RESTAURANT_ID,
                    f"device_{next_status or resolved_mode or next_state}",
                    _utc_now_iso(),
                ),
            )
            logger.info(
                "MQTT bridge: synchronized snapshot state=%s mode=%s status=%s",
                next_state,
                resolved_mode,
                next_status,
            )


def _handle_device_message(topic: str, payload: str) -> None:
    snapshot = snapshot_from_message(topic, payload)
    if len(snapshot) <= 2:
        logger.info("MQTT bridge: ignoring unrecognized payload on %s", topic)
        return
    _update_device_snapshot(snapshot)


def connect() -> None:
    """Connect to AWS IoT Core. Call once at app startup."""
    global _client
    try:
        _client = IoTMQTTClient(
            client_id="backend_server_01",
            on_message=_handle_device_message,
        )
        _client.connect(timeout=10.0)
        logger.info("MQTT bridge: connected to AWS IoT Core")
        sync_device_schedule(RESTAURANT_ID, force=True)
    except Exception as e:
        logger.warning(
            "MQTT bridge: failed to connect – %s (MQTT commands will be skipped)", e
        )
        _client = None


def disconnect() -> None:
    """Disconnect from AWS IoT Core. Call at app shutdown."""
    global _client
    if _client is not None:
        try:
            _client.disconnect()
        except Exception:
            pass
        _client = None
        logger.info("MQTT bridge: disconnected")


def publish_light_command(state: str) -> None:
    """Publish a light command to the ESP32 command topic. No-op if not connected."""
    if _client is None or not _client.is_connected:
        logger.warning(
            "MQTT bridge: not connected – skipping command '%s'", state
        )
        return
    try:
        _client.publish_command(state)
        logger.info("MQTT bridge: published '%s'", state)
    except Exception as e:
        logger.error("MQTT bridge: publish failed – %s", e)


def sync_device_schedule(restaurant_id: int, force: bool = False) -> str | None:
    """
    Publish today's schedule in the firmware's native payload format.
    """
    del force  # kept for a stable call signature as scheduler evolves

    if _client is None or not _client.is_connected:
        logger.warning(
            "MQTT bridge: not connected – skipping schedule sync for restaurant %s",
            restaurant_id,
        )
        return None

    schedule_on, schedule_off = get_effective_schedule_window(restaurant_id)

    try:
        payload = _client.publish_schedule(schedule_on, schedule_off)
        logger.info(
            "MQTT bridge: synced device schedule for restaurant %s (%s -> %s)",
            restaurant_id,
            schedule_on,
            schedule_off,
        )
        return payload
    except Exception as exc:
        logger.error("MQTT bridge: schedule sync failed – %s", exc)
        return None
