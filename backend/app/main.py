import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.db import init_db
from app.mqtt_bridge import connect as mqtt_connect, disconnect as mqtt_disconnect
from app.routes.lights import router as lights_router
from app.scheduler import start_scheduler, stop_scheduler

_env = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env)

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


app = FastAPI(
    title="Restaurant Lighting API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(lights_router)
