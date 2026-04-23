"""
MQTT bridge – connects the FastAPI backend to AWS IoT Core.

Manages a persistent IoTMQTTClient and exposes a simple publish function
that the service layer calls when light state changes.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

# Resolve cert paths relative to project root before importing the client
for _var in ("AWS_IOT_CA_CERT", "AWS_IOT_BACKEND_CERT", "AWS_IOT_BACKEND_KEY"):
    _val = os.getenv(_var, "")
    if _val and not os.path.isabs(_val):
        os.environ[_var] = str(PROJECT_ROOT / _val)

from aws.mqtt_client import IoTMQTTClient  # noqa: E402

from app.database.db import get_connection

logger = logging.getLogger(__name__)

_client: IoTMQTTClient | None = None
RESTAURANT_ID = 1


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _apply_telemetry_state(payload: str) -> None:
    """Persist device-reported state so API consumers reflect actual load status."""
    normalized = payload.strip().upper()
    if normalized == "LOAD=ON":
        next_state = "on"
    elif normalized == "LOAD=OFF":
        next_state = "off"
    else:
        logger.info("MQTT bridge: ignoring unrecognized telemetry payload '%s'", payload)
        return

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT state, brightness, schedule_on, schedule_off
            FROM restaurant_lights
            WHERE restaurant_id = ?
            """,
            (RESTAURANT_ID,),
        )
        row = cursor.fetchone()

        previous_state = row["state"] if row else None
        current_brightness = row["brightness"] if row else 0
        schedule_on = row["schedule_on"] if row else None
        schedule_off = row["schedule_off"] if row else None
        next_brightness = current_brightness if next_state == "on" and current_brightness > 0 else (85 if next_state == "on" else 0)

        cursor.execute(
            """
            INSERT INTO restaurant_lights (
                restaurant_id, state, brightness, schedule_on, schedule_off, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(restaurant_id) DO UPDATE SET
                state = excluded.state,
                brightness = excluded.brightness,
                schedule_on = excluded.schedule_on,
                schedule_off = excluded.schedule_off,
                last_updated = excluded.last_updated
            """,
            (RESTAURANT_ID, next_state, next_brightness, schedule_on, schedule_off, _utc_now_iso()),
        )

        if previous_state != next_state:
            cursor.execute(
                """
                INSERT INTO light_history (restaurant_id, action, timestamp)
                VALUES (?, ?, ?)
                """,
                (RESTAURANT_ID, f"telemetry_{next_state}", _utc_now_iso()),
            )
            logger.info("MQTT bridge: synchronized DB state to '%s' from telemetry", next_state)


def connect() -> None:
    """Connect to AWS IoT Core. Call once at app startup."""
    global _client
    try:
        _client = IoTMQTTClient(
            client_id="backend_server_01",
            on_telemetry=_apply_telemetry_state,
        )
        _client.connect(timeout=10.0)
        logger.info("MQTT bridge: connected to AWS IoT Core")
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
    """Publish 'on' or 'off' to the ESP32 command topic. No-op if not connected."""
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
