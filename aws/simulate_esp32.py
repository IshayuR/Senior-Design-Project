#!/usr/bin/env python3
"""
ESP32 device simulator.

Mimics the real ESP32 firmware's MQTT behaviour so the full pub/sub loop
can be validated before the physical hardware is available.

Uses the ESP32's OWN certificates (separate from the backend's certs).

Usage:
    python -m aws.simulate_esp32          # from project root
    python aws/simulate_esp32.py          # also works
"""

from __future__ import annotations

import logging
import os
import json
import signal
import ssl
import sys
import time
from datetime import datetime

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from aws.device_protocol import parse_device_message
from aws.iot_topics import DEVICE_ID, KEEPALIVE, PORT, TOPIC_CMD, TOPIC_SCHEDULE, TOPIC_STATUS, TOPIC_TELEMETRY

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ESP32-SIM] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
TELEMETRY_INTERVAL_SECONDS = 5.0


def _resolve_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(PROJECT_ROOT, path)


ENDPOINT = os.getenv("AWS_IOT_ENDPOINT", "")
CA_CERT = os.getenv("AWS_IOT_CA_CERT", "")
ESP32_CERT = os.getenv("AWS_IOT_ESP32_CERT", "")
ESP32_KEY = os.getenv("AWS_IOT_ESP32_KEY", "")

def _require(name: str, value: str) -> str:
    if not value:
        logger.error("Missing env var: %s", name)
        sys.exit(1)
    return value


class ESP32Simulator:
    def __init__(self) -> None:
        endpoint = _require("AWS_IOT_ENDPOINT", ENDPOINT)
        ca = _resolve_path(_require("AWS_IOT_CA_CERT", CA_CERT))
        cert = _resolve_path(_require("AWS_IOT_ESP32_CERT", ESP32_CERT))
        key = _resolve_path(_require("AWS_IOT_ESP32_KEY", ESP32_KEY))

        for path, label in [(ca, "CA cert"), (cert, "ESP32 cert"), (key, "ESP32 key")]:
            if not os.path.isfile(path):
                logger.error("%s not found: %s", label, path)
                sys.exit(1)

        self._endpoint = endpoint
        self._connected = False
        self._load_on = False
        self._mode = "auto"
        self._schedule = {f"s{index}_{field}": 0 for index in range(1, 7) for field in ("en", "start_h", "start_m", "end_h", "end_m")}
        self._last_telemetry_monotonic = 0.0

        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=DEVICE_ID,
            protocol=mqtt.MQTTv311,
        )
        self._client.tls_set(
            ca_certs=ca,
            certfile=cert,
            keyfile=key,
            tls_version=ssl.PROTOCOL_TLSv1_2,
        )
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
            logger.info("Connected to AWS IoT Core as '%s'", DEVICE_ID)
            for topic in (TOPIC_CMD, TOPIC_SCHEDULE):
                client.subscribe(topic, qos=1)
                logger.info("Subscribed to %s", topic)
            self._connected = True

            self._publish_status("boot")
            self._publish_status("online")
            self._publish_telemetry(force=True)
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
        logger.info("Received device message ← [%s]: '%s'", msg.topic, payload)

        if msg.topic == TOPIC_CMD:
            normalized = payload.upper()
            if normalized == "ON":
                self._load_on = True
                self._mode = "manual"
                self._publish_status("manual_on")
            elif normalized == "OFF":
                self._load_on = False
                self._mode = "manual"
                self._publish_status("manual_off")
            elif normalized == "AUTO":
                self._mode = "auto"
                self._publish_status("auto_mode")
            elif normalized == "DEMO":
                self._mode = "demo"
                self._load_on = False
                self._publish_status("demo_mode")
            else:
                logger.warning("Unrecognized command: '%s'", payload)
                return

            self._publish_telemetry()
            return

        if msg.topic == TOPIC_SCHEDULE:
            parsed = parse_device_message(payload)
            if parsed is None:
                self._publish_status("schedule_parse_error")
                return

            self._schedule.update(
                {
                    key: int(parsed.get(key, 0))
                    for key in self._schedule
                }
            )
            self._mode = "auto"
            self._publish_status("schedule_updated")
            self._apply_auto_schedule(force_publish=True)

    def _publish_status(self, status: str) -> None:
        body = json.dumps(
            {
                "device": DEVICE_ID,
                "status": status,
                "ip": "127.0.0.1",
                "uptime": int(time.monotonic()),
            },
            separators=(",", ":"),
        )
        self._client.publish(TOPIC_STATUS, body, qos=1)
        logger.info("Published status '%s' → %s", status, TOPIC_STATUS)

    def _publish_telemetry(self, force: bool = False) -> None:
        if not force and (time.monotonic() - self._last_telemetry_monotonic) < TELEMETRY_INTERVAL_SECONDS:
            return

        body = {
            "device": DEVICE_ID,
            "uptime": int(time.monotonic()),
            "RMSvoltage": 120.0,
            "maxVoltage": 170.0,
            "current": 0.82 if self._load_on else 0.0,
            "power": 98.4 if self._load_on else 0.0,
            "load": 1 if self._load_on else 0,
            "mode": self._mode,
            "schedule_type": "off_blocks",
        }
        body.update(self._schedule)
        payload = json.dumps(body, separators=(",", ":"))
        self._client.publish(TOPIC_TELEMETRY, payload, qos=1)
        self._last_telemetry_monotonic = time.monotonic()
        logger.info("Published telemetry → %s", TOPIC_TELEMETRY)

    def _should_be_on_in_auto_mode(self) -> bool:
        now = datetime.now()
        current_minute_of_day = (now.hour * 60) + now.minute
        should_be_on = True

        for index in range(1, 7):
            if int(self._schedule.get(f"s{index}_en", 0)) != 1:
                continue

            start_minute = (int(self._schedule.get(f"s{index}_start_h", 0)) * 60) + int(
                self._schedule.get(f"s{index}_start_m", 0)
            )
            end_minute = (int(self._schedule.get(f"s{index}_end_h", 0)) * 60) + int(
                self._schedule.get(f"s{index}_end_m", 0)
            )

            if start_minute < end_minute:
                if start_minute <= current_minute_of_day < end_minute:
                    should_be_on = False
                    break
            elif start_minute > end_minute:
                if current_minute_of_day >= start_minute or current_minute_of_day < end_minute:
                    should_be_on = False
                    break
            else:
                should_be_on = False
                break

        return should_be_on

    def _apply_auto_schedule(self, force_publish: bool = False) -> None:
        if self._mode != "auto":
            return

        next_load_on = self._should_be_on_in_auto_mode()
        state_changed = next_load_on != self._load_on
        self._load_on = next_load_on

        if state_changed or force_publish:
            self._publish_telemetry(force=True)

    def run(self) -> None:
        logger.info("Connecting to %s:%d …", self._endpoint, PORT)
        self._client.connect(self._endpoint, PORT, KEEPALIVE)

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
                self._apply_auto_schedule()
                self._publish_telemetry()
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass

        logger.info("Shutting down …")
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("Done")


if __name__ == "__main__":
    ESP32Simulator().run()
