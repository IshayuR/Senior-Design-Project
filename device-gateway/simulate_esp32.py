#!/usr/bin/env python3
"""
ESP32 device simulator.

Mimics the real ESP32 firmware's MQTT behaviour so the full pub/sub loop
can be validated before the physical hardware is available.

Uses the ESP32's OWN certificates (separate from the backend's certs).

Usage (from device-gateway folder):
    python simulate_esp32.py
"""

from __future__ import annotations

import logging
import os
import signal
import ssl
import sys
import time

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(_SCRIPT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ESP32-SIM] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _resolve_cert_path(path: str) -> str:
    """Resolve relative paths (e.g. ./file.pem) relative to device-gateway folder."""
    p = Path(path)
    if not p.is_absolute():
        p = _SCRIPT_DIR / p
    return str(p.resolve())


ENDPOINT = os.getenv("AWS_IOT_ENDPOINT", "")
CA_CERT = _resolve_cert_path(os.getenv("AWS_IOT_CA_CERT", "") or "./AmazonRootCA1.pem")
ESP32_CERT = _resolve_cert_path(os.getenv("AWS_IOT_ESP32_CERT", "") or "./certificate.pem.crt")
ESP32_KEY = _resolve_cert_path(os.getenv("AWS_IOT_ESP32_KEY", "") or "./private.pem.key")

# Local broker (default): no AWS/certs; run e.g. docker run -p 1883:1883 eclipse-mosquitto
# Uncomment the AWS block in __init__ and comment the local block to use AWS IoT.
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_LOCAL_PORT = int(os.getenv("MQTT_LOCAL_PORT", "1883"))

DEVICE_ID = "ESP32_Device_01"
TOPIC_CMD = f"esp32/{DEVICE_ID}/cmd"
TOPIC_TELE = f"esp32/{DEVICE_ID}/tele"

PORT = 8883
KEEPALIVE = 60


def _require(name: str, value: str) -> str:
    if not value:
        logger.error("Missing env var: %s", name)
        sys.exit(1)
    return value


class ESP32Simulator:
    def __init__(self) -> None:
        self._connected = False

        # --- Local broker (default): no certs ---
        self._host = MQTT_BROKER
        self._port = MQTT_LOCAL_PORT
        logger.info("Local MQTT: %s:%d (no certs)", self._host, self._port)
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=DEVICE_ID,
            protocol=mqtt.MQTTv311,
        )

        # --- AWS IoT (comment out local block above and uncomment below) ---
        # endpoint = _require("AWS_IOT_ENDPOINT", ENDPOINT)
        # ca, cert, key = CA_CERT, ESP32_CERT, ESP32_KEY
        # for path, label in [(ca, "CA cert"), (cert, "ESP32 cert"), (key, "ESP32 key")]:
        #     if not os.path.isfile(path):
        #         logger.error("%s not found: %s", label, path)
        #         sys.exit(1)
        # self._host = endpoint
        # self._port = PORT
        # self._client = mqtt.Client(
        #     callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        #     client_id=DEVICE_ID,
        #     protocol=mqtt.MQTTv311,
        # )
        # self._client.tls_set(
        #     ca_certs=ca,
        #     certfile=cert,
        #     keyfile=key,
        #     tls_version=ssl.PROTOCOL_TLSv1_2,
        # )

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        if reason_code == 0:
            logger.info("Connected as '%s'", DEVICE_ID)
            client.subscribe(TOPIC_CMD, qos=1)
            logger.info("Subscribed to %s", TOPIC_CMD)
            self._connected = True

            client.publish(TOPIC_TELE, "boot", qos=1)
            logger.info("Published 'boot' → %s", TOPIC_TELE)
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
        logger.warning("Disconnected (rc=%s)", reason_code)

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: object,
        msg: mqtt.MQTTMessage,
    ) -> None:
        payload = msg.payload.decode("utf-8", errors="replace").strip()
        logger.info("Received cmd ← [%s]: '%s'", msg.topic, payload)

        if payload == "on":
            response = "LOAD=ON"
        elif payload == "off":
            response = "LOAD=OFF"
        else:
            response = f"UNKNOWN_CMD:{payload}"
            logger.warning("Unrecognised command: '%s'", payload)

        logger.info("%s", response)
        self._client.publish(TOPIC_TELE, response, qos=1)
        logger.info("Published '%s' → %s", response, TOPIC_TELE)

    def run(self) -> None:
        logger.info("Connecting to %s:%d …", self._host, self._port)
        self._client.connect(self._host, self._port, KEEPALIVE)

        shutdown = False

        def _handle_signal(sig: int, frame: object) -> None:
            nonlocal shutdown
            shutdown = True

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        self._client.loop_start()

        deadline = time.monotonic() + 10
        while not self._connected and time.monotonic() < deadline:
            time.sleep(0.1)

        if not self._connected:
            logger.error("Timed out waiting for connection")
            self._client.loop_stop()
            sys.exit(1)

        logger.info("ESP32 simulator running — press Ctrl+C to stop")

        try:
            while not shutdown:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass

        logger.info("Shutting down …")
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("Done")


if __name__ == "__main__":
    ESP32Simulator().run()
