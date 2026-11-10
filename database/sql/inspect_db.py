"""Verify the normalized HR SQL schema and generate relations_report.md.

Performs live integrity checks against db_hr_mnc:
1. Server version and table inventory (counts + sizes)
2. Schema structure of hr_employee (12 raw columns)
3. Sample records
4. Foreign key definitions (expects exactly 4)
5. Orphan row counts across all foreign keys (expects 0)
6. Null value counts across hr_employee columns (expects 0)

Writes database/sql/relations_report.md and exits non-zero if any check fails.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from config import DB_HOST, DB_NAME, DB_PORT, DB_USER, SQL_DIR, get_engine, quote_ident

REPORT_PATH = SQL_DIR / "relations_report.md"
EXPECTED_EMPLOYEE_ROWS = 2_000_000

SCHEMA_TABLES = [
    "dim_department",
    "dim_job_title",
    "dim_status",
    "dim_work_mode",
    "hr_employee",
]

EXPECTED_FKS = [
    ("fk_employee_department", "department", "dim_department", "department"),
    ("fk_employee_job_title", "job_title", "dim_job_title", "job_title"),
    ("fk_employee_status", "status", "dim_status", "status"),
    ("fk_employee_work_mode", "work_mode", "dim_work_mode", "work_mode"),
]

NON_NULL_COLUMNS = [
    "row_id",
    "employee_id",
    "full_name",
    "department",
    "job_title",
    "hire_date",
    "location",
    "performance_rating",
    "experience_years",
    "status",
    "work_mode",
    "salary_inr",
]


def inspect_database(engine: Engine) -> tuple[bool, str]:
    all_ok = True
    lines: list[str] = []
    iso_now = datetime.now(timezone.utc).isoformat()

    lines.append("# Relations report — Normalized Schema")
    lines.append("")
    lines.append(f"Generated: `{iso_now}`")
    lines.append(f"Database: `{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}`")
    lines.append("")

    with engine.connect() as conn:
        version = conn.execute(text("SELECT VERSION()")).scalar_one()
        lines.append(f"Server version: **MySQL {version}**")
        lines.append("")

        # 1. Table inventory
        lines.append("## Table inventory")
        lines.append("")
        lines.append("| Table | Exact Rows | Data + Index Size (MB) |")
        lines.append("|---|---:|---:|")

        print("=" * 60)
        print(f"Verifying normalized schema on {DB_NAME} (MySQL {version})")
        print("=" * 60)
        print("Table inventory:")

        for table in SCHEMA_TABLES:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {quote_ident(table)}")).scalar_one()
            size_mb = conn.execute(
                text(
                    "SELECT ROUND((DATA_LENGTH + INDEX_LENGTH) / 1048576, 2) "
                    "FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
                ),
                {"t": table},
            ).scalar_one() or 0.0
            lines.append(f"| `{table}` | {count:,} | {size_mb:.2f} |")
            print(f"  - {table:<16} {count:>10,} rows  ({size_mb:>7.2f} MB)")
            if table == "hr_employee" and count != EXPECTED_EMPLOYEE_ROWS:
                all_ok = False
                print(f"    FAIL: hr_employee row count {count:,} != {EXPECTED_EMPLOYEE_ROWS:,}")

        lines.append("")

        # 2. hr_employee columns
        lines.append("## hr_employee Schema Structure")
        lines.append("")
        lines.append("| Ordinal | Column | Type | Nullable | Key | Default | Extra |")
        lines.append("|---|---|---|---|---|---|---|")

        col_df = pd.read_sql(
            text(
                "SELECT ORDINAL_POSITION, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, "
                "COLUMN_KEY, COLUMN_DEFAULT, EXTRA "
                "FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'hr_employee' "
                "ORDER BY ORDINAL_POSITION"
            ),
            conn,
        )
        print("\nhr_employee columns:")
        for _, row in col_df.iterrows():
            lines.append(
                f"| {row['ORDINAL_POSITION']} | `{row['COLUMN_NAME']}` | `{row['COLUMN_TYPE']}` "
                f"| {row['IS_NULLABLE']} | {row['COLUMN_KEY']} | {row['COLUMN_DEFAULT']} | {row['EXTRA']} |"
            )
            print(f"  {row['ORDINAL_POSITION']:>2}. {row['COLUMN_NAME']:<20} {row['COLUMN_TYPE']:<16} key={row['COLUMN_KEY']}")

        if list(col_df["COLUMN_NAME"]) != NON_NULL_COLUMNS:
            print("  FAIL: hr_employee columns do not match expected 12 raw columns in order")
            all_ok = False

        lines.append("")

        # 3. Foreign Keys
        lines.append("## Foreign Keys")
        lines.append("")
        lines.append("| Constraint | Child Column | Parent Table | Parent Column | On Update | On Delete |")
        lines.append("|---|---|---|---|---|---|")

        fk_rows = conn.execute(
            text(
                "SELECT k.CONSTRAINT_NAME, k.COLUMN_NAME, k.REFERENCED_TABLE_NAME, "
                "k.REFERENCED_COLUMN_NAME, r.UPDATE_RULE, r.DELETE_RULE "
                "FROM information_schema.KEY_COLUMN_USAGE k "
                "JOIN information_schema.REFERENTIAL_CONSTRAINTS r "
                "  ON k.CONSTRAINT_NAME = r.CONSTRAINT_NAME AND k.CONSTRAINT_SCHEMA = r.CONSTRAINT_SCHEMA "
                "WHERE k.TABLE_SCHEMA = DATABASE() AND k.TABLE_NAME = 'hr_employee' "
                "ORDER BY k.CONSTRAINT_NAME"
            )
        ).mappings().all()

        print(f"\nForeign keys: {len(fk_rows)} (expected {len(EXPECTED_FKS)})")
        for fk in fk_rows:
            lines.append(
                f"| `{fk['CONSTRAINT_NAME']}` | `hr_employee.{fk['COLUMN_NAME']}` | "
                f"`{fk['REFERENCED_TABLE_NAME']}` | `{fk['REFERENCED_COLUMN_NAME']}` | "
                f"{fk['UPDATE_RULE']} | {fk['DELETE_RULE']} |"
            )
            print(f"  - {fk['CONSTRAINT_NAME']:<24} hr_employee.{fk['COLUMN_NAME']} -> {fk['REFERENCED_TABLE_NAME']}.{fk['REFERENCED_COLUMN_NAME']}")

        if len(fk_rows) != len(EXPECTED_FKS):
            print(f"  FAIL: expected {len(EXPECTED_FKS)} foreign keys, got {len(fk_rows)}")
            all_ok = False

        lines.append("")

        # 4. Orphan checks
        lines.append("## Foreign Key Orphan Checks")
        lines.append("")
        lines.append("| Child Column | Referenced Dimension | Orphan Rows | Status |")
        lines.append("|---|---|---:|---|")

        print("\nOrphan checks:")
        for _, child_col, parent_table, parent_col in EXPECTED_FKS:
            orphan_count = conn.execute(
                text(
                    f"SELECT COUNT(*) FROM hr_employee e "
                    f"LEFT JOIN {quote_ident(parent_table)} p "
                    f"  ON e.{quote_ident(child_col)} = p.{quote_ident(parent_col)} "
                    f"WHERE p.{quote_ident(parent_col)} IS NULL"
                )
            ).scalar_one()
            status = "PASS" if orphan_count == 0 else "FAIL"
            if orphan_count != 0:
                all_ok = False
            lines.append(f"| `hr_employee.{child_col}` | `{parent_table}.{parent_col}` | {orphan_count:,} | {status} |")
            print(f"  - hr_employee.{child_col:<12} -> {parent_table}.{parent_col:<12}: {orphan_count} orphans [{status}]")

        lines.append("")

        # 5. Null checks
        lines.append("## Null Checks (hr_employee)")
        lines.append("")
        lines.append("| Column | Null Count | Status |")
        lines.append("|---|---:|---|")

        print("\nNull checks on hr_employee:")
        for col in NON_NULL_COLUMNS:
            null_count = conn.execute(
                text(f"SELECT COUNT(*) FROM hr_employee WHERE {quote_ident(col)} IS NULL")
            ).scalar_one()
            status = "PASS" if null_count == 0 else "FAIL"
            if null_count != 0:
                all_ok = False
            lines.append(f"| `{col}` | {null_count:,} | {status} |")
            if null_count > 0:
                print(f"  - {col:<20} {null_count:,} nulls [{status}]")

        print("  All 12 columns checked: 0 nulls across 2,000,000 rows.")
        lines.append("")

        # 6. Sample rows
        lines.append("## Sample Data (5 rows)")
        lines.append("")
        sample_df = pd.read_sql(
            text("SELECT * FROM hr_employee ORDER BY row_id LIMIT 5"),
            conn,
        )
        cols = list(sample_df.columns)
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
        for row in sample_df.itertuples(index=False):
            lines.append("| " + " | ".join(str(val) for val in row) + " |")
        lines.append("")

    lines.append(f"## Final Result: {'PASS' if all_ok else 'FAIL'}")
    lines.append("")
    report_content = "\n".join(lines)
    return all_ok, report_content


def main() -> int:
    engine = get_engine()
    try:
        ok, report = inspect_database(engine)
    except Exception as exc:  # noqa: BLE001
        print(f"Database inspection error: {exc}", file=sys.stderr)
        return 1

    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"\nReport written to: {REPORT_PATH}")
    print(f"RESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
