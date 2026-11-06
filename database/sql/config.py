"""Central configuration for the HR analytics SQL package.

Credentials and paths are read from a .env file.  Nothing secret is hard-coded.
The engine is created with PyMySQL + SQLAlchemy.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL

SQL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SQL_DIR.parents[1]
OUTPUT_DIR = SQL_DIR / "output"

# Load .env from database/sql first, then from the project root.  Existing
# environment variables are not overwritten.
for _candidate in (SQL_DIR / ".env", PROJECT_ROOT / ".env"):
    if _candidate.exists():
        load_dotenv(_candidate, override=False)

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "db_hr_mnc")


def _resolve_path(value: str, default: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path if value else default


DATA_DIR = Path(os.getenv("HR_DATA_DIR", str(PROJECT_ROOT / "data-science" / "output")))
FEATURES_PARQUET = _resolve_path(
    os.getenv("HR_FEATURES_PARQUET", ""), DATA_DIR / "hr_features.parquet"
)
BRANCH_CSV = _resolve_path(
    os.getenv("BRANCH_EFFICIENCY_CSV", ""), DATA_DIR / "new_dataset_branch_efficiency.csv"
)


def get_engine(echo: bool = False) -> Engine:
    """Build a SQLAlchemy engine using credentials from .env."""
    url = URL.create(
        "mysql+pymysql",
        username=DB_USER,
        password=DB_PASSWORD or None,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        query={"charset": "utf8mb4"},
    )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=echo,
        future=True,
    )


def quote_ident(name: str) -> str:
    """Safely quote a MySQL identifier."""
    return "`" + name.replace("`", "``") + "`"
