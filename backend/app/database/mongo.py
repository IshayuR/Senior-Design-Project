import os
from functools import lru_cache

from pymongo import MongoClient


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

