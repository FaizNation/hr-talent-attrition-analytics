"""Central configuration for the Firestore NoSQL package.

Credentials and database settings are loaded from .env.
Service account keys and database passwords are never hardcoded.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

FIRESTORE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = FIRESTORE_DIR.parents[1]

# 1. Load database/firestore/.env first
if (FIRESTORE_DIR / ".env").exists():
    load_dotenv(FIRESTORE_DIR / ".env", override=False)

# 2. Fallback to database/sql/.env or root .env
for _candidate in (FIRESTORE_DIR.parent / "sql" / ".env", PROJECT_ROOT / ".env"):
    if _candidate.exists():
        load_dotenv(_candidate, override=False)

FIREBASE_CREDENTIALS_PATH_RAW = os.getenv("FIREBASE_CREDENTIALS_PATH", "")


def get_firebase_credentials_path() -> Path:
    if not FIREBASE_CREDENTIALS_PATH_RAW:
        raise ValueError(
            "FIREBASE_CREDENTIALS_PATH is not set in environment or database/firestore/.env"
        )
    p = Path(FIREBASE_CREDENTIALS_PATH_RAW).expanduser()
    if not p.is_absolute():
        if (FIRESTORE_DIR / p).exists():
            p = (FIRESTORE_DIR / p).resolve()
        else:
            p = (PROJECT_ROOT / p).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Firebase credentials file not found at: {p}")
    return p


_FIRESTORE_CLIENT = None


def get_firestore_client():
    """Build and cache a google-cloud-firestore Client via firebase_admin."""
    global _FIRESTORE_CLIENT
    if _FIRESTORE_CLIENT is not None:
        return _FIRESTORE_CLIENT

    import firebase_admin
    from firebase_admin import credentials, firestore

    cred_path = get_firebase_credentials_path()
    try:
        app = firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate(str(cred_path))
        app = firebase_admin.initialize_app(cred)

    _FIRESTORE_CLIENT = firestore.client(app=app)
    return _FIRESTORE_CLIENT


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
