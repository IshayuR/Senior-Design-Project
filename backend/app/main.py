from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.db import init_db
from app.database.mongo import get_mongo_client, get_user_collection
from app.routes.auth import router as auth_router
from app.routes.lights import router as lights_router

# Load .env from backend directory so MONGODB_URI / MONGODB_DB_NAME are set
_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env)

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
    # Verify MongoDB connection (used for auth). Log only; do not crash if unreachable.
    try:
        get_mongo_client().admin.command("ping")
        get_user_collection()  # ensure DB/collection accessible
        print("MongoDB: connected")
    except Exception as e:
        print("MongoDB: not available:", e)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(lights_router)
