"""
MongoDB connection for SD_IoT database. Set MONGODB_URI and optional MONGODB_DB_NAME in .env.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from pymongo import MongoClient
from pymongo.database import Database

if TYPE_CHECKING:
    pass

# e.g. mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net/SD_IoT
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "SD_IoT")

_client: MongoClient | None = None


def get_mongo_client() -> MongoClient:
    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI is not set; add it to .env to use MongoDB.")
    global _client
    if _client is None:
        _client = MongoClient(
        MONGODB_URI,
        maxPoolSize=10,          
        minPoolSize=1,           
        maxIdleTimeMS=60000,     
        retryWrites=True,          
        retryReads=True          
        )
    return _client


def get_mongo_db() -> Database:
    return get_mongo_client()[MONGODB_DB_NAME]
