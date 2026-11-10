"""Copy raw HR data from hr_attrition into the normalized hr_employee table.

Chunked, idempotent set-based copy in row_id ranges.
"""
from __future__ import annotations

import argparse
import sys
import time

from sqlalchemy import text
from sqlalchemy.engine import Engine

from config import get_engine
from create_schema import populate_dimensions

EXPECTED_ROWS = 2_000_000
DEFAULT_BATCH_ROWS = 100_000


def preflight_asserts(engine: Engine) -> None:
    """Validate source invariants before touching hr_employee.

    Raises SystemExit(1) on failure.
    """
    with engine.connect() as conn:
        invalid_dates = conn.execute(
            text(
                "SELECT COUNT(*) FROM hr_attrition "
                "WHERE hire_date IS NULL OR STR_TO_DATE(hire_date, '%Y-%m-%d') IS NULL"
            )
        ).scalar_one()
        if invalid_dates != 0:
            sys.exit(f"FAIL: {invalid_dates} invalid or null hire_date values in hr_attrition")

        max_len = conn.execute(
            text("SELECT MAX(CHAR_LENGTH(location)) FROM hr_attrition")
        ).scalar_one()
        if max_len > 120:
            sys.exit(f"FAIL: max location length {max_len} exceeds VARCHAR(120)")

        dept_src = conn.execute(
            text("SELECT COUNT(DISTINCT department) FROM hr_attrition")
        ).scalar_one()
        dept_dim = conn.execute(text("SELECT COUNT(*) FROM dim_department")).scalar_one()
        if dept_src != dept_dim:
            sys.exit(
                f"FAIL: dim_department has {dept_dim} rows but hr_attrition has {dept_src} distinct departments"
            )
    print("Pre-flight asserts: PASS")


def load_employee(engine: Engine, batch_rows: int = DEFAULT_BATCH_ROWS) -> int:
    """Copy rows in row_id slices with one commit per batch so it can resume."""
    with engine.connect() as conn:
        current_rows = conn.execute(text("SELECT COUNT(*) FROM hr_employee")).scalar_one()
        if current_rows == EXPECTED_ROWS:
            print(f"hr_employee already has {current_rows:,} rows; skipping load.")
            return 0
        max_id = conn.execute(text("SELECT IFNULL(MAX(row_id), -1) FROM hr_attrition")).scalar_one()

    print("Ensuring dimensions are populated...")
    populate_dimensions(engine)

    total_inserted = 0
    start_time = time.perf_counter()
    copy_sql = """
        INSERT IGNORE INTO hr_employee (
            row_id, employee_id, full_name, department, job_title, hire_date,
            location, performance_rating, experience_years, status, work_mode, salary_inr
        )
        SELECT row_id, employee_id, full_name, department, job_title,
               STR_TO_DATE(hire_date, '%Y-%m-%d'), location,
               performance_rating, experience_years, status, work_mode, salary_inr
        FROM hr_attrition
        WHERE row_id >= :start AND row_id < :end
    """

    for start in range(0, max_id + 1, batch_rows):
        end = start + batch_rows
        with engine.begin() as conn:
            res = conn.execute(text(copy_sql), {"start": start, "end": end})
            total_inserted += res.rowcount
            elapsed = time.perf_counter() - start_time
            rate = (end if end <= max_id + 1 else max_id + 1) / elapsed if elapsed > 0 else 0
            print(
                f"\r  copied up to row_id {end:,}/{max_id + 1:,} "
                f"({res.rowcount:,} inserted this batch, {rate:,.0f} rows/s)",
                end="",
                flush=True,
            )
    print()
    return total_inserted


def verify_load(engine: Engine) -> bool:
    with engine.connect() as conn:
        attrition_count = conn.execute(text("SELECT COUNT(*) FROM hr_attrition")).scalar_one()
        employee_count = conn.execute(text("SELECT COUNT(*) FROM hr_employee")).scalar_one()

    print(f"  hr_attrition rows : {attrition_count:,}")
    print(f"  hr_employee rows  : {employee_count:,}")
    ok = (attrition_count == EXPECTED_ROWS) and (employee_count == EXPECTED_ROWS)
    print("Post-load verification:", "PASS" if ok else "FAIL")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_ROWS,
        help=f"Number of rows per batch (default: {DEFAULT_BATCH_ROWS})",
    )
    args = parser.parse_args()

    engine = get_engine()
    try:
        with engine.connect() as conn:
            print(f"Connected to {conn.execute(text('SELECT DATABASE()')).scalar_one()}")
    except Exception as exc:  # noqa: BLE001
        print(f"Could not connect to MySQL: {exc}", file=sys.stderr)
        return 1

    preflight_asserts(engine)
    load_employee(engine, batch_rows=args.batch_size)
    if not verify_load(engine):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
