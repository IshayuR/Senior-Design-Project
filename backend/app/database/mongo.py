import os
import re
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

# Load repo-root .env before any os.getenv (import order in main.py can vary under uvicorn reload)
# mongo.py: database/ -> app/ -> backend/ -> repo/
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_ROOT / ".env")


def _get_mongo_uri() -> str:
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    return uri


def _get_db_name() -> str:
    return os.getenv("MONGODB_DB_NAME", "restaurant_lighting")


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    uri = _get_mongo_uri()
    return MongoClient(uri)


def get_user_collection():
    client = get_mongo_client()
    db = client[_get_db_name()]
    return db["users"]


def get_schedule_collection():
    client = get_mongo_client()
    db = client[_get_db_name()]
    return db["schedules"]


def email_match_filter(email: str) -> dict:
    """Case-insensitive exact email match (avoids regex special-char issues in local part)."""
    e = email.strip()
    escaped = re.escape(e)
    return {"email": {"$regex": f"^{escaped}$", "$options": "i"}}
