"""Chunked, idempotent loading of the two processed datasets.

* hr_features.parquet  -> hr_features  (2,000,000 rows)
* new_dataset_branch_efficiency.csv -> branch_efficiency (3,402 rows)

Rows are read in 50,000-row chunks and inserted with INSERT IGNORE so the
script can be re-run safely.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Iterable

import pandas as pd
import pyarrow.parquet as pq
from sqlalchemy import text
from sqlalchemy.engine import Engine

from config import BRANCH_CSV, FEATURES_PARQUET, get_engine

HR_COLUMNS = [
    "employee_id",
    "department",
    "job_title",
    "country",
    "city",
    "work_mode",
    "status",
    "performance_rating",
    "experience_years",
    "tenure_years",
    "salary_inr",
    "salary_disparity_index",
    "performance_to_exp_ratio",
    "talent_segment",
]

PARQUET_RENAME = {
    "Employee_ID": "employee_id",
    "Department": "department",
    "Job_Title": "job_title",
    "Country": "country",
    "City": "city",
    "Work_Mode": "work_mode",
    "Status": "status",
    "Performance_Rating": "performance_rating",
    "Experience_Years": "experience_years",
    "Tenure_Years": "tenure_years",
    "Salary_INR": "salary_inr",
    "Salary_Disparity_Index": "salary_disparity_index",
    "Performance_to_Exp_Ratio": "performance_to_exp_ratio",
    "Talent_Segment": "talent_segment",
}

BRANCH_COLUMNS = [
    "country",
    "department",
    "work_mode",
    "total_employees",
    "attrition_count",
    "turnover_rate_pct",
    "avg_salary_disparity",
    "avg_performance",
]

BRANCH_RENAME = {
    "Country": "country",
    "Department": "department",
    "Work_Mode": "work_mode",
    "Total_Employees": "total_employees",
    "Attrition_Count": "attrition_count",
    "Turnover_Rate_Pct": "turnover_rate_pct",
    "Avg_Salary_Disparity": "avg_salary_disparity",
    "Avg_Performance": "avg_performance",
}

HR_INSERT = (
    "INSERT IGNORE INTO hr_features ("
    + ", ".join(HR_COLUMNS)
    + ") VALUES ("
    + ", ".join(["%s"] * len(HR_COLUMNS))
    + ")"
)

BRANCH_INSERT = (
    "INSERT IGNORE INTO branch_efficiency ("
    + ", ".join(BRANCH_COLUMNS)
    + ") VALUES ("
    + ", ".join(["%s"] * len(BRANCH_COLUMNS))
    + ")"
)


def table_count(engine: Engine, table: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one()


def table_exists(engine: Engine, table: str) -> bool:
    with engine.connect() as conn:
        return bool(
            conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name = :t"
                ),
                {"t": table},
            ).scalar_one()
        )


def dataframe_rows(df: pd.DataFrame, columns: list[str]) -> list[tuple]:
    """Convert a pandas chunk to Python-native tuples (numpy -> Python)."""
    ordered = df.loc[:, columns].astype(object)
    ordered = ordered.where(pd.notna(ordered), None)
    return list(ordered.itertuples(index=False, name=None))


def insert_batches(cursor, sql: str, rows: list[tuple], batch_size: int) -> int:
    inserted = 0
    for start in range(0, len(rows), batch_size):
        cursor.executemany(sql, rows[start : start + batch_size])
        inserted += cursor.rowcount
    return inserted


def print_progress(label: str, processed: int, total: int, inserted: int, started: float) -> None:
    elapsed = time.perf_counter() - started
    pct = (100.0 * processed / total) if total else 100.0
    rate = processed / elapsed if elapsed else 0.0
    print(
        f"\r  {label}: {processed:,}/{total:,} ({pct:5.1f}%) "
        f"inserted={inserted:,} {rate:,.0f} rows/s",
        end="",
        flush=True,
    )


def load_parquet(engine: Engine, path: Path, chunk_size: int, insert_batch: int) -> int:
    if not path.exists():
        raise FileNotFoundError(f"Parquet not found: {path}")
    parquet_file = pq.ParquetFile(path)
    total = parquet_file.metadata.num_rows
    current = table_count(engine, "hr_features")
    if current == total:
        print(f"  hr_features already has {current:,} rows; skipping load.")
        return 0
    if current > total:
        raise RuntimeError(
            f"hr_features has {current:,} rows, more than the parquet's {total:,}."
        )

    print(f"  Loading {path.name} -> hr_features ({total:,} rows)")
    if current:
        print(f"  Resuming: {current:,} rows already present; duplicates will be ignored.")

    raw = engine.raw_connection()
    cursor = raw.cursor()
    inserted = 0
    processed = 0
    started = time.perf_counter()
    try:
        for batch in parquet_file.iter_batches(batch_size=chunk_size):
            frame = batch.to_pandas().rename(columns=PARQUET_RENAME)
            rows = dataframe_rows(frame, HR_COLUMNS)
            inserted += insert_batches(cursor, HR_INSERT, rows, insert_batch)
            raw.commit()
            processed += len(rows)
            print_progress("hr_features", processed, total, inserted, started)
    finally:
        cursor.close()
        raw.close()
    print()
    return inserted


def load_branch_csv(engine: Engine, path: Path, chunk_size: int, insert_batch: int) -> int:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    total = len(pd.read_csv(path, usecols=[0]))
    current = table_count(engine, "branch_efficiency")
    if current == total:
        print(f"  branch_efficiency already has {current:,} rows; skipping load.")
        return 0
    if current > total:
        raise RuntimeError(
            f"branch_efficiency has {current:,} rows, more than the CSV's {total:,}."
        )

    print(f"  Loading {path.name} -> branch_efficiency ({total:,} rows)")
    if current:
        print(f"  Resuming: {current:,} rows already present; duplicates will be ignored.")

    raw = engine.raw_connection()
    cursor = raw.cursor()
    inserted = 0
    processed = 0
    started = time.perf_counter()
    try:
        for frame in pd.read_csv(path, chunksize=chunk_size):
            frame = frame.rename(columns=BRANCH_RENAME)
            rows = dataframe_rows(frame, BRANCH_COLUMNS)
            inserted += insert_batches(cursor, BRANCH_INSERT, rows, insert_batch)
            raw.commit()
            processed += len(rows)
            print_progress("branch_efficiency", processed, total, inserted, started)
    finally:
        cursor.close()
        raw.close()
    print()
    return inserted


def verify(engine: Engine) -> bool:
    print("\nVerifying loaded data")
    ok = True

    with engine.connect() as conn:
        hr_count = conn.execute(text("SELECT COUNT(*) FROM hr_features")).scalar_one()
        branch_count = conn.execute(
            text("SELECT COUNT(*) FROM branch_efficiency")
        ).scalar_one()
        print(f"  hr_features       : {hr_count:,}")
        print(f"  branch_efficiency : {branch_count:,}")

        if hr_count != 2_000_000:
            print("  FAIL: hr_features should have 2,000,000 rows")
            ok = False
        if branch_count != 3_402:
            print("  FAIL: branch_efficiency should have 3,402 rows")
            ok = False

        orphan_ids = conn.execute(
            text(
                "SELECT COUNT(*) FROM hr_features f "
                "LEFT JOIN hr_attrition a ON f.employee_id = a.employee_id "
                "WHERE a.employee_id IS NULL"
            )
        ).scalar_one()
        print(f"  feature rows without raw employee : {orphan_ids:,}")
        if orphan_ids:
            ok = False

        orphan_branch = conn.execute(
            text(
                "SELECT COUNT(*) FROM hr_features f "
                "LEFT JOIN branch_efficiency b "
                "  ON f.country = b.country "
                " AND f.department = b.department "
                " AND f.work_mode = b.work_mode "
                "WHERE b.country IS NULL"
            )
        ).scalar_one()
        print(f"  feature rows without branch       : {orphan_branch:,}")
        if orphan_branch:
            ok = False

        empty_branches = conn.execute(
            text(
                "SELECT COUNT(*) FROM branch_efficiency b "
                "LEFT JOIN hr_features f "
                "  ON f.country = b.country "
                " AND f.department = b.department "
                " AND f.work_mode = b.work_mode "
                "WHERE f.employee_id IS NULL"
            )
        ).scalar_one()
        print(f"  branch rows without features      : {empty_branches:,}")
        if empty_branches:
            ok = False

        distinct_branches = conn.execute(
            text(
                "SELECT COUNT(DISTINCT country, department, work_mode) "
                "FROM branch_efficiency"
            )
        ).scalar_one()
        branch_employee_total = conn.execute(
            text("SELECT SUM(total_employees) FROM branch_efficiency")
        ).scalar_one()
        print(f"  distinct branch combinations      : {distinct_branches:,}")
        print(f"  SUM(branch total_employees)       : {branch_employee_total:,}")
        if distinct_branches != branch_count:
            print("  FAIL: branch primary key is not unique")
            ok = False
        if branch_employee_total != 2_000_000:
            print("  FAIL: branch totals should sum to 2,000,000")
            ok = False

    print("  verification:", "PASS" if ok else "FAIL")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunk-size", type=int, default=50_000)
    parser.add_argument("--insert-batch", type=int, default=5_000)
    args = parser.parse_args()

    engine = get_engine()
    for table in ("hr_features", "branch_efficiency", "hr_attrition"):
        if not table_exists(engine, table):
            print(
                f"Table {table!r} is missing. Run create_schema.py --phase base first.",
                file=sys.stderr,
            )
            return 1

    print("Loading processed datasets")
    started = time.perf_counter()
    try:
        load_parquet(engine, FEATURES_PARQUET, args.chunk_size, args.insert_batch)
        load_branch_csv(engine, BRANCH_CSV, args.chunk_size, args.insert_batch)
    except Exception as exc:  # noqa: BLE001 - report a clean error
        print(f"\nLoad failed: {exc}", file=sys.stderr)
        return 1

    ok = verify(engine)
    print(f"\nTotal load time: {time.perf_counter() - started:.1f}s")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
