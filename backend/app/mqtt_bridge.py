"""
MQTT bridge – connects the FastAPI backend to AWS IoT Core.

Manages a persistent IoTMQTTClient and exposes a simple publish function
that the service layer calls when light state changes.
"""

from __future__ import annotations

import logging
import os
import sys
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

logger = logging.getLogger(__name__)

_client: IoTMQTTClient | None = None


def connect() -> None:
    """Connect to AWS IoT Core. Call once at app startup."""
    global _client
    try:
        _client = IoTMQTTClient(client_id="backend_server_01")
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
