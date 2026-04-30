"""
Backend MQTT client for AWS IoT Core.

Connects to the IoT broker using TLS mutual authentication and provides
methods to publish commands to the ESP32 and receive telemetry responses.
"""

from __future__ import annotations

import logging
import os
import ssl
import time
from datetime import date
from typing import Callable

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from aws.device_protocol import build_schedule_payload, normalize_light_command
from aws.iot_topics import KEEPALIVE, PORT, TOPIC_CMD, TOPIC_SCHEDULE, TOPIC_STATUS, TOPIC_TELEMETRY

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

logger = logging.getLogger(__name__)

ENDPOINT = os.getenv("AWS_IOT_ENDPOINT", "")
CA_CERT = os.getenv("AWS_IOT_CA_CERT", "")
BACKEND_CERT = os.getenv("AWS_IOT_BACKEND_CERT", "")
BACKEND_KEY = os.getenv("AWS_IOT_BACKEND_KEY", "")


def _resolve_path(path: str) -> str:
    """Resolve relative cert paths from the project root, not CWD."""
    if os.path.isabs(path):
        return path
    return os.path.join(PROJECT_ROOT, path)


def _require_env(name: str, value: str) -> str:
    if not value:
        raise EnvironmentError(f"Missing required environment variable: {name}")
    return value


class IoTMQTTClient:
    """Manages the MQTT connection between the Python backend and AWS IoT Core."""

    def __init__(
        self,
        client_id: str = "backend_server_01",
        on_message: Callable[[str, str], None] | None = None,
    ) -> None:
        self._client_id = client_id
        self._user_message_cb = on_message
        self._connected = False

        endpoint = _require_env("AWS_IOT_ENDPOINT", ENDPOINT)
        ca = _resolve_path(_require_env("AWS_IOT_CA_CERT", CA_CERT))
        cert = _resolve_path(_require_env("AWS_IOT_BACKEND_CERT", BACKEND_CERT))
        key = _resolve_path(_require_env("AWS_IOT_BACKEND_KEY", BACKEND_KEY))

        for path, label in [(ca, "CA cert"), (cert, "Backend cert"), (key, "Backend key")]:
            if not os.path.isfile(path):
                raise FileNotFoundError(f"{label} not found at: {path}")

        self._endpoint = endpoint
        self._ca = ca
        self._cert = cert
        self._key = key

        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=self._client_id,
            protocol=mqtt.MQTTv311,
        )
        self._client.tls_set(
            ca_certs=self._ca,
            certfile=self._cert,
            keyfile=self._key,
            tls_version=ssl.PROTOCOL_TLSv1_2,
        )

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    # ── Callbacks ───────────────────────────────────────────────────────

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        if reason_code == 0:
            logger.info("Connected to AWS IoT Core as '%s'", self._client_id)
            for topic in (TOPIC_TELEMETRY, TOPIC_STATUS):
                client.subscribe(topic, qos=1)
                logger.info("Subscribed to %s", topic)
            self._connected = True
        else:
            logger.error("Connection failed — reason code: %s", reason_code)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        self._connected = False
        logger.warning("Disconnected from AWS IoT Core (rc=%s)", reason_code)

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: object,
        msg: mqtt.MQTTMessage,
    ) -> None:
        payload = msg.payload.decode("utf-8", errors="replace")
        logger.info("Device message ← [%s]: %s", msg.topic, payload)
        if self._user_message_cb:
            self._user_message_cb(msg.topic, payload)

    # ── Public API ──────────────────────────────────────────────────────

    def connect(self, timeout: float = 10.0) -> None:
        """Connect to AWS IoT Core and start the network loop."""
        logger.info("Connecting to %s:%d …", self._endpoint, PORT)
        self._client.connect(self._endpoint, PORT, KEEPALIVE)
        self._client.loop_start()

        deadline = time.monotonic() + timeout
        while not self._connected and time.monotonic() < deadline:
            time.sleep(0.1)

        if not self._connected:
            self._client.loop_stop()
            raise ConnectionError(
                f"Timed out after {timeout}s waiting for MQTT connection"
            )

    def disconnect(self) -> None:
        """Cleanly disconnect from the broker."""
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("Disconnected from AWS IoT Core")

    def publish_command(self, command: str) -> None:
        """Publish a command (e.g. 'ON' / 'OFF' / 'AUTO' / 'DEMO') to the device."""
        if not self._connected:
            raise ConnectionError("Not connected to AWS IoT Core")
        normalized = normalize_light_command(command)
        info = self._client.publish(TOPIC_CMD, normalized, qos=1)
        info.wait_for_publish(timeout=5)
        logger.info("Command → [%s]: %s", TOPIC_CMD, normalized)

    def publish_schedule(
        self,
        schedule_date: date,
        schedule_on: str | None,
        schedule_off: str | None,
    ) -> str:
        """Publish the firmware-specific schedule payload and return the JSON sent."""
        if not self._connected:
            raise ConnectionError("Not connected to AWS IoT Core")
        payload = build_schedule_payload(schedule_date, schedule_on, schedule_off)
        info = self._client.publish(TOPIC_SCHEDULE, payload, qos=1)
        info.wait_for_publish(timeout=5)
        logger.info("Schedule → [%s]: %s", TOPIC_SCHEDULE, payload)
        return payload

    @property
    def is_connected(self) -> bool:
        return self._connected
