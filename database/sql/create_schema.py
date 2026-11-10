"""Create the normalized SQL schema for the HR runway project.

Phases
------
base    : create the four dimension tables and the hr_employee fact table,
          then populate the dimensions from the raw hr_attrition table.
explain : capture EXPLAIN plans for the reporting queries.

Everything is idempotent.  The only destructive path is --drop-legacy, and it
refuses to run unless hr_employee already holds the full 2,000,000 rows.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

from config import OUTPUT_DIR, get_engine, quote_ident

EXPECTED_EMPLOYEE_ROWS = 2_000_000

EMPLOYEE_COLUMNS = [
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

DIMENSION_TABLES = ["dim_department", "dim_job_title", "dim_status", "dim_work_mode"]
SCHEMA_TABLES = DIMENSION_TABLES + ["hr_employee"]
LEGACY_TABLES = [
    "hr_features",
    "branch_efficiency",
    "hr_attrition",
    "dim_country",
    "dim_talent_segment",
]

DDL = {
    "dim_department": """
        CREATE TABLE IF NOT EXISTS dim_department (
            department VARCHAR(10) NOT NULL,
            PRIMARY KEY (department)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """,
    "dim_job_title": """
        CREATE TABLE IF NOT EXISTS dim_job_title (
            job_title VARCHAR(29) NOT NULL,
            PRIMARY KEY (job_title)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """,
    "dim_status": """
        CREATE TABLE IF NOT EXISTS dim_status (
            status VARCHAR(10) NOT NULL,
            PRIMARY KEY (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """,
    "dim_work_mode": """
        CREATE TABLE IF NOT EXISTS dim_work_mode (
            work_mode VARCHAR(7) NOT NULL,
            PRIMARY KEY (work_mode)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """,
    "hr_employee": """
        CREATE TABLE IF NOT EXISTS hr_employee (
            row_id INT UNSIGNED NOT NULL,
            employee_id CHAR(10) NOT NULL,
            full_name VARCHAR(64) NOT NULL,
            department VARCHAR(10) NOT NULL,
            job_title VARCHAR(29) NOT NULL,
            hire_date DATE NOT NULL,
            location VARCHAR(120) NOT NULL,
            performance_rating TINYINT UNSIGNED NOT NULL,
            experience_years TINYINT UNSIGNED NOT NULL,
            status VARCHAR(10) NOT NULL,
            work_mode VARCHAR(7) NOT NULL,
            salary_inr INT UNSIGNED NOT NULL,
            PRIMARY KEY (row_id),
            UNIQUE KEY uq_employee_id (employee_id),
            KEY idx_employee_department (department),
            KEY idx_employee_job_title (job_title),
            KEY idx_employee_status (status),
            KEY idx_employee_work_mode (work_mode),
            KEY idx_employee_hire_date (hire_date),
            CONSTRAINT fk_employee_department FOREIGN KEY (department)
                REFERENCES dim_department (department),
            CONSTRAINT fk_employee_job_title FOREIGN KEY (job_title)
                REFERENCES dim_job_title (job_title),
            CONSTRAINT fk_employee_status FOREIGN KEY (status)
                REFERENCES dim_status (status),
            CONSTRAINT fk_employee_work_mode FOREIGN KEY (work_mode)
                REFERENCES dim_work_mode (work_mode)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """,
}

# Dimensions are populated from the raw source table before any fact rows move,
# so the foreign keys on hr_employee can be enforced inline.
DIM_POPULATION = [
    (
        "dim_department",
        """
        INSERT IGNORE INTO dim_department (department)
        SELECT DISTINCT department FROM hr_attrition
        WHERE department IS NOT NULL AND department <> ''
        """,
    ),
    (
        "dim_job_title",
        """
        INSERT IGNORE INTO dim_job_title (job_title)
        SELECT DISTINCT job_title FROM hr_attrition
        WHERE job_title IS NOT NULL AND job_title <> ''
        """,
    ),
    (
        "dim_status",
        """
        INSERT IGNORE INTO dim_status (status)
        SELECT DISTINCT status FROM hr_attrition
        WHERE status IS NOT NULL AND status <> ''
        """,
    ),
    (
        "dim_work_mode",
        """
        INSERT IGNORE INTO dim_work_mode (work_mode)
        SELECT DISTINCT work_mode FROM hr_attrition
        WHERE work_mode IS NOT NULL AND work_mode <> ''
        """,
    ),
]

EXPLAIN_QUERIES = {
    "department_headcount": "SELECT department, COUNT(*) FROM hr_employee GROUP BY department",
    "salary_by_job_title": "SELECT job_title, AVG(salary_inr) FROM hr_employee GROUP BY job_title",
}


def table_exists(conn, table: str) -> bool:
    return bool(
        conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = :t"
            ),
            {"t": table},
        ).scalar_one()
    )


def create_tables(engine: Engine) -> None:
    with engine.begin() as conn:
        for table, ddl in DDL.items():
            conn.execute(text(ddl))
            print(f"  {table:<16} ok")
    with engine.connect() as conn:
        for table in SCHEMA_TABLES:
            exists = table_exists(conn, table)
            print(f"  {table:<16} {'present' if exists else 'MISSING'}")
            if not exists:
                raise SystemExit(f"Table {table} was not created.")


def populate_dimensions(engine: Engine) -> None:
    with engine.begin() as conn:
        if not table_exists(conn, "hr_attrition"):
            # After the legacy drop, dimensions are already populated; skip.
            print("  hr_attrition missing; dimensions left as they are.")
        else:
            for table, sql in DIM_POPULATION:
                conn.execute(text(sql))
    with engine.connect() as conn:
        for table in DIMENSION_TABLES:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            print(f"  {table:<16} {count:,} rows")


def verify_schema(engine: Engine) -> bool:
    """Structural check of the normalized schema. Returns False on any mismatch."""
    ok = True
    with engine.connect() as conn:
        for table in SCHEMA_TABLES:
            exists = table_exists(conn, table)
            print(f"  {table:<16} {'present' if exists else 'MISSING'}")
            ok = ok and exists
        if not table_exists(conn, "hr_employee"):
            print("  column check skipped: hr_employee missing")
            return False

        columns = [
            r[0]
            for r in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = DATABASE() AND table_name = 'hr_employee' "
                    "ORDER BY ordinal_position"
                )
            )
        ]
        if columns != EMPLOYEE_COLUMNS:
            print(f"  FAIL columns: {columns}")
            ok = False
        else:
            print(f"  hr_employee columns: {len(columns)} raw fields, ordered")

        fks = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.table_constraints "
                "WHERE table_schema = DATABASE() AND table_name = 'hr_employee' "
                "AND constraint_type = 'FOREIGN KEY'"
            )
        ).scalar_one()
        print(f"  hr_employee foreign keys: {fks}")
        ok = ok and fks == 4

    print("  schema verification:", "PASS" if ok else "FAIL")
    return ok


def capture_explain(conn, name: str, sql: str) -> list[dict]:
    rows = conn.execute(text(f"EXPLAIN {sql}")).mappings().all()
    return [{k: str(v) for k, v in row.items()} for row in rows]


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"  wrote {path.relative_to(OUTPUT_DIR.parents[1])}")


def run_explain(engine: Engine) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    captured = {}
    with engine.connect() as conn:
        for name, sql in EXPLAIN_QUERIES.items():
            captured[name] = {"sql": sql, "plan": capture_explain(conn, name, sql)}
            print(f"  {name:<24} {len(captured[name]['plan'])} step(s)")
    payload = {
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "schema": "normalized raw (hr_employee + 4 dims)",
        "queries": captured,
    }
    write_json(OUTPUT_DIR / "explain_after.json", payload)


def drop_legacy(engine: Engine, assume_yes: bool) -> int:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT COUNT(*) FROM hr_employee")).scalar_one()
        present = [t for t in LEGACY_TABLES if table_exists(conn, t)]
    if rows != EXPECTED_EMPLOYEE_ROWS:
        print(
            f"REFUSING: hr_employee has {rows:,} rows, expected {EXPECTED_EMPLOYEE_ROWS:,}."
        )
        return 1
    if not verify_schema(engine):
        print("REFUSING: schema verification failed.")
        return 1
    if not present:
        print("Nothing to drop; legacy tables are already gone.")
        return 0

    print("Tables to drop:", ", ".join(present))
    if not assume_yes:
        answer = input("Type YES to drop the tables above: ").strip()
        if answer != "YES":
            print("Aborted; nothing was dropped.")
            return 1

    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in present:
            conn.execute(text(f"DROP TABLE IF EXISTS {quote_ident(table)}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        remaining = [
            r[0]
            for r in conn.execute(text("SHOW TABLES"))
        ]
    print("dropped:", ", ".join(present))
    print("remaining tables:", ", ".join(sorted(remaining)))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase", choices=["base", "explain"], default="base", help="which step to run"
    )
    parser.add_argument("--verify", action="store_true", help="only verify the schema")
    parser.add_argument(
        "--drop-legacy", action="store_true", help="drop the retired attrition tables"
    )
    parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = parser.parse_args()

    engine = get_engine()
    try:
        with engine.connect() as conn:
            print(f"Connected to {conn.execute(text('SELECT DATABASE()')).scalar_one()}")
    except Exception as exc:  # noqa: BLE001 - friendly startup error
        print(f"Could not connect to MySQL: {exc}", file=sys.stderr)
        return 1

    if args.verify:
        return 0 if verify_schema(engine) else 1

    if args.drop_legacy:
        return drop_legacy(engine, args.yes)

    if args.phase == "base":
        create_tables(engine)
        populate_dimensions(engine)
    else:
        run_explain(engine)
    return 0


if __name__ == "__main__":
    sys.exit(main())
