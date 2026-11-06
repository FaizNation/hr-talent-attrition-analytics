"""Central configuration for the HR analytics NoSQL package.

Credentials and URLs are loaded from .env.
Service account keys and database URLs are never hardcoded.
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

NOSQL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = NOSQL_DIR.parents[1]
EXPORT_DIR = NOSQL_DIR / "export"

# 1. Load database/nosql/.env first
if (NOSQL_DIR / ".env").exists():
    load_dotenv(NOSQL_DIR / ".env", override=False)

# 2. Fall back to database/sql/.env or root .env for MySQL credentials if needed
for _candidate in (NOSQL_DIR.parent / "sql" / ".env", PROJECT_ROOT / ".env"):
    if _candidate.exists():
        load_dotenv(_candidate, override=False)

# Firebase Settings
FIREBASE_CREDENTIALS_PATH_RAW = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL", "").rstrip("/")


def get_firebase_credentials_path() -> Path:
    """Resolve Firebase service account key path securely."""
    if not FIREBASE_CREDENTIALS_PATH_RAW:
        raise ValueError(
            "FIREBASE_CREDENTIALS_PATH is not set in environment or database/nosql/.env"
        )
    p = Path(FIREBASE_CREDENTIALS_PATH_RAW).expanduser()
    if not p.is_absolute():
        # Check relative to database/nosql first, then PROJECT_ROOT
        if (NOSQL_DIR / p).exists():
            p = (NOSQL_DIR / p).resolve()
        else:
            p = (PROJECT_ROOT / p).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Firebase credentials file not found at: {p}")
    return p


# MySQL Settings
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "db_hr_mnc")


def get_mysql_engine():
    """Build SQLAlchemy engine for reading from MySQL."""
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
