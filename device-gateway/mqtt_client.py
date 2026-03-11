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
from typing import Callable

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

ENDPOINT = os.getenv("AWS_IOT_ENDPOINT", "")
CA_CERT = os.getenv("AWS_IOT_CA_CERT", "")
BACKEND_CERT = os.getenv("AWS_IOT_BACKEND_CERT", "")
BACKEND_KEY = os.getenv("AWS_IOT_BACKEND_KEY", "")

DEVICE_ID = "ESP32_Device_01"
TOPIC_CMD = f"esp32/{DEVICE_ID}/cmd"
TOPIC_TELE = f"esp32/{DEVICE_ID}/tele"

PORT = 8883
KEEPALIVE = 60


def _require_env(name: str, value: str) -> str:
    if not value:
        raise EnvironmentError(f"Missing required environment variable: {name}")
    return value


class IoTMQTTClient:
    """Manages the MQTT connection between the Python backend and AWS IoT Core."""

    def __init__(
        self,
        client_id: str = "backend_server_01",
        on_telemetry: Callable[[str], None] | None = None,
    ) -> None:
        self._client_id = client_id
        self._user_telemetry_cb = on_telemetry
        self._connected = False

        endpoint = _require_env("AWS_IOT_ENDPOINT", ENDPOINT)
        ca = _require_env("AWS_IOT_CA_CERT", CA_CERT)
        cert = _require_env("AWS_IOT_BACKEND_CERT", BACKEND_CERT)
        key = _require_env("AWS_IOT_BACKEND_KEY", BACKEND_KEY)

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
            client.subscribe(TOPIC_TELE, qos=1)
            logger.info("Subscribed to %s", TOPIC_TELE)
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
        logger.info("Telemetry ← [%s]: %s", msg.topic, payload)
        if self._user_telemetry_cb:
            self._user_telemetry_cb(payload)

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
        """Publish a command (e.g. 'on' / 'off') to the ESP32 cmd topic."""
        if not self._connected:
            raise ConnectionError("Not connected to AWS IoT Core")
        info = self._client.publish(TOPIC_CMD, command, qos=1)
        info.wait_for_publish(timeout=5)
        logger.info("Command → [%s]: %s", TOPIC_CMD, command)

    @property
    def is_connected(self) -> bool:
        return self._connected


# ── Backwards-compatible helper for Flask app and scheduler ───────────────
# If BACKEND certs are set → use IoTMQTTClient (topic esp32/.../cmd, payload "on"/"off").
# Else → use config.py (CA_CERT, CERTFILE, KEYFILE) and same topic so simulate_esp32 receives.

_singleton_client: IoTMQTTClient | None = None


def publish_light_state(state: str) -> None:
    """Publish 'on' or 'off' to esp32/ESP32_Device_01/cmd (for app, scheduler, simulate_esp32)."""
    global _singleton_client
    # Local MQTT placeholder (no AWS/certs)
    try:
        from config import LOCAL_MQTT, MQTT_BROKER, MQTT_LOCAL_PORT
        if LOCAL_MQTT:
            client = mqtt.Client(client_id="gateway_local", protocol=mqtt.MQTTv311)
            client.connect(MQTT_BROKER, MQTT_LOCAL_PORT)
            client.publish(TOPIC_CMD, state, qos=1)
            client.disconnect()
            return
    except Exception:
        pass
    if BACKEND_CERT and BACKEND_KEY:
        if _singleton_client is None or not _singleton_client.is_connected:
            _singleton_client = IoTMQTTClient()
            _singleton_client.connect()
        _singleton_client.publish_command(state)
        return
    # Fallback: config.py env (same .env as scheduler)
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parent / ".env")
    endpoint = os.getenv("AWS_IOT_ENDPOINT", "")
    if not endpoint:
        raise RuntimeError("AWS_IOT_ENDPOINT not set; cannot connect to MQTT")
    root = Path(__file__).resolve().parent
    ca = os.getenv("CA_CERT") or str(root / "AmazonRootCA1.pem")
    cert = os.getenv("CERTFILE") or str(root / "certificate.pem.crt")
    key = os.getenv("KEYFILE") or str(root / "private.pem.key")
    for path, name in [(ca, "CA_CERT"), (cert, "CERTFILE"), (key, "KEYFILE")]:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"{name} not found: {path}")
    client = mqtt.Client(client_id=os.getenv("MQTT_CLIENT_ID", "gateway"), protocol=mqtt.MQTTv311)
    client.tls_set(ca_certs=ca, certfile=cert, keyfile=key, tls_version=ssl.PROTOCOL_TLSv1_2)
    client.connect(endpoint, PORT)
    client.publish(TOPIC_CMD, state, qos=1)
    client.disconnect()
