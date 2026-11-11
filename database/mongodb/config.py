"""Central configuration for the MongoDB NoSQL package.

Credentials and database settings are loaded from .env.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

MONGODB_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MONGODB_DIR.parents[1]

# 1. Load database/mongodb/.env first
if (MONGODB_DIR / ".env").exists():
    load_dotenv(MONGODB_DIR / ".env", override=False)

# 2. Fallback to database/sql/.env or root .env
for _candidate in (MONGODB_DIR.parent / "sql" / ".env", PROJECT_ROOT / ".env"):
    if _candidate.exists():
        load_dotenv(_candidate, override=False)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "db_hr_mnc")

_MONGO_CLIENT = None


def get_mongo_client():
    """Build and cache a PyMongo MongoClient instance."""
    global _MONGO_CLIENT
    if _MONGO_CLIENT is not None:
        return _MONGO_CLIENT
    from pymongo import MongoClient

    _MONGO_CLIENT = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _MONGO_CLIENT


def get_mongo_db():
    """Return the target MongoDB database."""
    client = get_mongo_client()
    return client[MONGO_DB_NAME]


DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "db_hr_mnc")


def get_mysql_engine():
    """Build SQLAlchemy engine for reading from MySQL master."""
    from sqlalchemy import create_engine
    from sqlalchemy.engine import URL

    url = URL.create(
        "mysql+pymysql",
        username=DB_USER,
        password=DB_PASSWORD or None,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        query={"charset": "utf8mb4"},
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600, future=True)
