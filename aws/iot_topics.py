"""
Shared AWS IoT Core topic and client configuration.
"""

from __future__ import annotations

import os


DEVICE_ID = os.getenv("AWS_IOT_DEVICE_ID", "ESP32_Device_01")

TOPIC_CMD = f"esp32/{DEVICE_ID}/cmd"
TOPIC_SCHEDULE = f"esp32/{DEVICE_ID}/schedule"
TOPIC_TELEMETRY = f"esp32/{DEVICE_ID}/tele"
TOPIC_STATUS = f"esp32/{DEVICE_ID}/status"

PORT = 8883
KEEPALIVE = 60
