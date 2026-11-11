"""Stream and load 2,000,000 raw employee records from MySQL into MongoDB.

Target:
- Database: db_hr_mnc
- Collection: employees (2,000,000 documents)

Uses chunked streaming (50,000 rows per batch) and bulk insert_many.
Builds secondary indexes on department, job_title, status, work_mode, and salary_inr.
"""
from __future__ import annotations

import argparse
import sys
import time
from typing import Any

from pymongo import ASCENDING
from sqlalchemy import text
from sqlalchemy.engine import Engine

from config import get_mongo_db, get_mysql_engine

EXPECTED_ROWS = 2_000_000
DEFAULT_CHUNK_SIZE = 50_000


def create_indexes(collection) -> None:
    """Build secondary indexes on frequently queried fields."""
    print("Building secondary indexes on 'employees' collection...")
    t0 = time.time()
    collection.create_index([("department", ASCENDING)])
    collection.create_index([("job_title", ASCENDING)])
    collection.create_index([("status", ASCENDING)])
    collection.create_index([("work_mode", ASCENDING)])
    collection.create_index([("salary_inr", ASCENDING)])
    print(f"Indexes created successfully in {time.time()-t0:.2f}s")


def load_employees(
    mysql_engine: Engine, mongo_db: Any, chunk_size: int = DEFAULT_CHUNK_SIZE
) -> int:
    collection = mongo_db["employees"]
    current_count = collection.count_documents({})
    if current_count == EXPECTED_ROWS:
        print(
            f"Collection 'employees' already contains {current_count:,} documents. Skipping load."
        )
        return current_count

    print(
        f"Starting streaming load from MySQL 'hr_employee' to MongoDB 'employees' (chunk size: {chunk_size:,})..."
    )
    t_start = time.time()

    with mysql_engine.connect() as conn:
        max_id = conn.execute(
            text("SELECT IFNULL(MAX(row_id), -1) FROM hr_employee")
        ).scalar_one()

    query_template = """
        SELECT
            row_id, employee_id, full_name, department, job_title,
            hire_date, location, performance_rating, experience_years,
            status, work_mode, salary_inr
        FROM hr_employee
        WHERE row_id >= :start AND row_id < :end
        ORDER BY row_id
    """

    total_inserted = 0
    with mysql_engine.connect() as conn:
        for start in range(0, max_id + 1, chunk_size):
            end = start + chunk_size
            rows = (
                conn.execute(text(query_template), {"start": start, "end": end})
                .mappings()
                .all()
            )
            if not rows:
                continue

            docs = [
                {
                    "_id": str(r["employee_id"]),
                    "row_id": int(r["row_id"]),
                    "employee_id": str(r["employee_id"]),
                    "full_name": str(r["full_name"]),
                    "department": str(r["department"]),
                    "job_title": str(r["job_title"]),
                    "hire_date": str(r["hire_date"]),
                    "location": str(r["location"]),
                    "performance_rating": int(r["performance_rating"]),
                    "experience_years": int(r["experience_years"]),
                    "status": str(r["status"]),
                    "work_mode": str(r["work_mode"]),
                    "salary_inr": int(r["salary_inr"]),
                }
                for r in rows
            ]

            try:
                collection.insert_many(docs, ordered=False)
                total_inserted += len(docs)
            except Exception as exc:
                # Handle resume or duplicates gracefully
                if "duplicate key error" in str(exc):
                    total_inserted += len(docs)
                else:
                    raise exc

            elapsed = time.time() - t_start
            rate = total_inserted / elapsed if elapsed > 0 else 0
            pct = (
                (100.0 * total_inserted / EXPECTED_ROWS)
                if EXPECTED_ROWS
                else 100.0
            )
            print(
                f"\r  inserted {total_inserted:,}/{EXPECTED_ROWS:,} ({pct:5.1f}%) — {rate:,.0f} docs/s",
                end="",
                flush=True,
            )

    print(f"\nBulk streaming completed in {time.time()-t_start:.2f}s")
    create_indexes(collection)

    final_count = collection.count_documents({})
    print(f"Total documents in 'employees': {final_count:,}")
    return final_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Rows per streaming chunk (default: 50,000)",
    )
    args = parser.parse_args()

    mongo_db = get_mongo_db()
    mysql_engine = get_mysql_engine()

    try:
        final_count = load_employees(
            mysql_engine, mongo_db, chunk_size=args.chunk_size
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Error during MongoDB load: {exc}", file=sys.stderr)
        return 1

    if final_count != EXPECTED_ROWS:
        print(
            f"FAIL: expected {EXPECTED_ROWS:,} documents, got {final_count:,}",
            file=sys.stderr,
        )
        return 1

    print("MongoDB load: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
