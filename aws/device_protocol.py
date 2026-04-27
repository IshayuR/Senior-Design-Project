"""
Helpers for translating between backend scheduling semantics and the
firmware's MQTT payload contract.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

MAX_SCHEDULE_BLOCKS = 6
MINUTES_PER_DAY = 24 * 60


@dataclass(frozen=True)
class ScheduleBlock:
    enabled: int
    start_h: int
    start_m: int
    end_h: int
    end_m: int


def normalize_light_command(state: str) -> str:
    normalized = state.strip().upper()
    aliases = {
        "ON": "ON",
        "OFF": "OFF",
        "AUTO": "AUTO",
        "DEMO": "DEMO",
    }
    if normalized not in aliases:
        raise ValueError(f"Unsupported device command: {state}")
    return aliases[normalized]


def _parse_hhmm(value: str) -> int:
    hour_text, minute_text = value.split(":", maxsplit=1)
    hour = int(hour_text)
    minute = int(minute_text)
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError(f"Invalid HH:MM time: {value}")
    return (hour * 60) + minute


def _block(start_minute: int, end_minute: int, enabled: bool = True) -> ScheduleBlock:
    start_minute %= MINUTES_PER_DAY
    end_minute %= MINUTES_PER_DAY
    return ScheduleBlock(
        enabled=1 if enabled else 0,
        start_h=start_minute // 60,
        start_m=start_minute % 60,
        end_h=end_minute // 60,
        end_m=end_minute % 60,
    )


def build_schedule_payload(schedule_on: str | None, schedule_off: str | None) -> str:
    """
    Convert a single UI "on window" into the firmware's 6-block "off window"
    JSON payload. Missing schedules become a full-day OFF block so the device
    behaves safely when auto mode is enabled.
    """

    blocks: list[ScheduleBlock]

    if not schedule_on or not schedule_off:
        blocks = [_block(0, 0)]
    else:
        start = _parse_hhmm(schedule_on)
        end = _parse_hhmm(schedule_off)

        if start == end:
            blocks = []
        elif start < end:
            blocks = []
            if start > 0:
                blocks.append(_block(0, start))
            if end < MINUTES_PER_DAY:
                blocks.append(_block(end, 0))
        else:
            blocks = [_block(end, start)]

    while len(blocks) < MAX_SCHEDULE_BLOCKS:
        blocks.append(_block(0, 0, enabled=False))

    payload: dict[str, int] = {}
    for index, block in enumerate(blocks[:MAX_SCHEDULE_BLOCKS], start=1):
        block_dict = asdict(block)
        payload[f"s{index}_en"] = block_dict["enabled"]
        payload[f"s{index}_start_h"] = block_dict["start_h"]
        payload[f"s{index}_start_m"] = block_dict["start_m"]
        payload[f"s{index}_end_h"] = block_dict["end_h"]
        payload[f"s{index}_end_m"] = block_dict["end_m"]

    return json.dumps(payload, separators=(",", ":"))


def parse_device_message(payload: str) -> dict[str, Any] | None:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def snapshot_from_message(topic: str, payload: str) -> dict[str, Any]:
    """
    Normalize firmware messages into a small backend-friendly snapshot.
    """

    message = parse_device_message(payload)
    snapshot: dict[str, Any] = {
        "topic": topic,
        "raw_payload": payload,
    }

    if message is None:
        normalized = payload.strip().upper()
        if normalized == "LOAD=ON":
            snapshot["state"] = "on"
        elif normalized == "LOAD=OFF":
            snapshot["state"] = "off"
        return snapshot

    snapshot["message"] = message

    if "load" in message:
        snapshot["state"] = "on" if int(message["load"]) else "off"
    elif message.get("status") == "manual_on":
        snapshot["state"] = "on"
    elif message.get("status") == "manual_off":
        snapshot["state"] = "off"

    if "mode" in message:
        snapshot["mode"] = str(message["mode"])
    elif "status" in message:
        snapshot["status"] = str(message["status"])

    if "ip" in message:
        snapshot["ip"] = str(message["ip"])

    return snapshot
