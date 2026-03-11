#!/usr/bin/env python3
"""
End-to-end connection test.

Sends 'on' and 'off' commands via the BACKEND certificates, then listens
for the matching telemetry responses on the tele topic.

Prerequisites:
  - simulate_esp32.py must be running in another terminal
  - .env must have both backend and ESP32 cert paths configured

Usage:
    python -m aws.test_connection        # from project root
    python aws/test_connection.py        # also works
"""

from __future__ import annotations

import logging
import sys
import threading
import time

sys.path.insert(0, ".")

from aws.mqtt_client import IoTMQTTClient  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TEST] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

TIMEOUT = 10  # seconds to wait for each response


def _run_test(client: IoTMQTTClient, command: str, expected: str) -> bool:
    """Publish *command*, wait up to TIMEOUT for *expected* on tele topic."""
    result: dict[str, str | None] = {"payload": None}
    event = threading.Event()

    original_cb = client._user_telemetry_cb

    def _capture(payload: str) -> None:
        result["payload"] = payload
        if payload == expected:
            event.set()
        if original_cb:
            original_cb(payload)

    client._user_telemetry_cb = _capture

    logger.info("Publishing command: '%s'", command)
    client.publish_command(command)

    received = event.wait(timeout=TIMEOUT)
    client._user_telemetry_cb = original_cb

    if received:
        logger.info("PASS  — sent '%s', received '%s'", command, result["payload"])
        return True

    logger.error(
        "FAIL  — sent '%s', expected '%s', got '%s' (timeout=%ds)",
        command,
        expected,
        result["payload"],
        TIMEOUT,
    )
    return False


def main() -> None:
    logger.info("=" * 50)
    logger.info("AWS IoT Core End-to-End Connection Test")
    logger.info("=" * 50)
    logger.info(
        "Make sure simulate_esp32.py is running in another terminal!"
    )
    logger.info("")

    client = IoTMQTTClient(client_id="backend_test_runner")

    try:
        client.connect(timeout=15)
    except (ConnectionError, FileNotFoundError, EnvironmentError) as exc:
        logger.error("Could not connect: %s", exc)
        sys.exit(1)

    time.sleep(1)

    results: list[bool] = []

    results.append(_run_test(client, "on", "LOAD=ON"))
    time.sleep(1)
    results.append(_run_test(client, "off", "LOAD=OFF"))

    client.disconnect()

    logger.info("")
    logger.info("=" * 50)
    passed = sum(results)
    total = len(results)
    if passed == total:
        logger.info("ALL TESTS PASSED (%d/%d)", passed, total)
    else:
        logger.error("SOME TESTS FAILED (%d/%d passed)", passed, total)
    logger.info("=" * 50)

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
