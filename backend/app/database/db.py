import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


DEFAULT_DB_PATH = Path(__file__).resolve().parent / "lights.db"
DB_PATH = Path(os.getenv("LIGHTS_DB_PATH", str(DEFAULT_DB_PATH)))

# Seed row for SQLite placeholder: one default restaurant light
SEED_RESTAURANT_ID = 1
SEED_INITIAL_STATE = "off"
SEED_INITIAL_BRIGHTNESS = 0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS restaurant_lights (
                restaurant_id INTEGER PRIMARY KEY,
                state TEXT NOT NULL CHECK(state IN ('on', 'off')),
                brightness INTEGER NOT NULL CHECK(brightness >= 0 AND brightness <= 100),
                schedule_on TEXT,
                schedule_off TEXT,
                last_updated TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS light_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            INSERT OR IGNORE INTO restaurant_lights (
                restaurant_id, state, brightness, schedule_on, schedule_off, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (SEED_RESTAURANT_ID, SEED_INITIAL_STATE, SEED_INITIAL_BRIGHTNESS, None, None, _utc_now_iso()),
        )
