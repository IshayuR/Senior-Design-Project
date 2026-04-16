import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Load repo-root .env before importing app modules that read os.environ (Mongo, etc.)
_env = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.db import init_db
from app.mqtt_bridge import connect as mqtt_connect, disconnect as mqtt_disconnect
from app.routes.auth import router as auth_router
from app.routes.lights import router as lights_router
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    mqtt_connect()
    start_scheduler()
    yield
    stop_scheduler()
    mqtt_disconnect()


logger = logging.getLogger(__name__)

app = FastAPI(title="Restaurant Lighting API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()

    from aws.mqtt_client import IoTMQTTClient

    def _on_telemetry(payload: str) -> None:
        logger.info("ESP32 telemetry: %s", payload)

    try:
        client = IoTMQTTClient(on_telemetry=_on_telemetry)
        client.connect()
        app.state.mqtt = client
        logger.info("MQTT client connected and ready")
    except Exception as exc:
        logger.warning("MQTT unavailable — backend will run without IoT: %s", exc)
        app.state.mqtt = None


@app.on_event("shutdown")
def on_shutdown() -> None:
    mqtt_client = getattr(app.state, "mqtt", None)
    if mqtt_client is not None:
        mqtt_client.disconnect()


@app.get("/health")
def health() -> dict[str, str]:
    mqtt_client = getattr(app.state, "mqtt", None)
    return {
        "status": "ok",
        "mqtt": "connected" if mqtt_client and mqtt_client.is_connected else "disconnected",
    }


app.include_router(lights_router)
app.include_router(auth_router)
