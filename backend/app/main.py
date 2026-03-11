import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.database.db import init_db
from app.routes.lights import router as lights_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Restaurant Lighting API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Local prototype only; tighten for production.
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
