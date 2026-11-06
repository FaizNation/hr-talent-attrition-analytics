"""Create the SQL schema for the HR analytics project.

Phases
------
base    : create the new tables, populate small dimension tables, and
          optionally apply the approved hr_attrition primary-key migration.
indexes : add secondary indexes and foreign keys, and capture EXPLAIN plans
          before/after indexing.

Everything is idempotent.  The only destructive statement is the
hr_attrition ALTER, and it is skipped unless --apply-pk is supplied and the
operator confirms it (or --yes is supplied).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

from config import OUTPUT_DIR, get_engine, quote_ident

EXPECTED_ATTRITION_ROWS = 2_000_000

DDL = {
    "dim_country": """
        CREATE TABLE IF NOT EXISTS dim_country (
            country VARCHAR(51) NOT NULL,
            PRIMARY KEY (country)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
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
    "dim_work_mode": """
        CREATE TABLE IF NOT EXISTS dim_work_mode (
            work_mode VARCHAR(7) NOT NULL,
            PRIMARY KEY (work_mode)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    "dim_status": """
        CREATE TABLE IF NOT EXISTS dim_status (
            status VARCHAR(10) NOT NULL,
            PRIMARY KEY (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    "dim_talent_segment": """
        CREATE TABLE IF NOT EXISTS dim_talent_segment (
            talent_segment VARCHAR(33) NOT NULL,
            PRIMARY KEY (talent_segment)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    "hr_features": """
        CREATE TABLE IF NOT EXISTS hr_features (
            employee_id CHAR(10) NOT NULL,
            department VARCHAR(10) NOT NULL,
            job_title VARCHAR(29) NOT NULL,
            country VARCHAR(51) NOT NULL,
            city VARCHAR(24) NOT NULL,
            work_mode VARCHAR(7) NOT NULL,
            status VARCHAR(10) NOT NULL,
            performance_rating TINYINT UNSIGNED NOT NULL,
            experience_years TINYINT UNSIGNED NOT NULL,
            tenure_years TINYINT UNSIGNED NOT NULL,
            salary_inr INT UNSIGNED NOT NULL,
            salary_disparity_index DECIMAL(12,10) NOT NULL,
            performance_to_exp_ratio DECIMAL(12,10) NOT NULL,
            talent_segment VARCHAR(33) NOT NULL,
            PRIMARY KEY (employee_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    "branch_efficiency": """
        CREATE TABLE IF NOT EXISTS branch_efficiency (
            country VARCHAR(51) NOT NULL,
            department VARCHAR(10) NOT NULL,
            work_mode VARCHAR(7) NOT NULL,
            total_employees SMALLINT UNSIGNED NOT NULL,
            attrition_count SMALLINT UNSIGNED NOT NULL,
            turnover_rate_pct DECIMAL(5,3) NOT NULL,
            avg_salary_disparity DECIMAL(6,4) NOT NULL,
            avg_performance DECIMAL(4,3) NOT NULL,
            PRIMARY KEY (country, department, work_mode)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
}

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
        "dim_work_mode",
        """
        INSERT IGNORE INTO dim_work_mode (work_mode)
        SELECT DISTINCT work_mode FROM hr_attrition
        WHERE work_mode IS NOT NULL AND work_mode <> ''
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
        "dim_country",
        """
        INSERT IGNORE INTO dim_country (country)
        SELECT DISTINCT TRIM(SUBSTRING_INDEX(location, ', ', -1))
        FROM hr_attrition
        WHERE location LIKE '%, %'
        """,
    ),
    (
        "dim_talent_segment",
        """
        INSERT IGNORE INTO dim_talent_segment (talent_segment)
        SELECT DISTINCT talent_segment FROM hr_features
        WHERE talent_segment IS NOT NULL AND talent_segment <> ''
        """,
    ),
    (
        "dim_country_from_branch",
        """
        INSERT IGNORE INTO dim_country (country)
        SELECT DISTINCT country FROM branch_efficiency
        WHERE country IS NOT NULL AND country <> ''
        """,
    ),
]

# table, index name, columns, unique
INDEXES = [
    ("hr_attrition", "uq_hr_attrition_employee_id", ["employee_id"], True),
    ("hr_attrition", "idx_hr_attrition_department", ["department"], False),
    ("hr_attrition", "idx_hr_attrition_status", ["status"], False),
    ("hr_attrition", "idx_hr_attrition_work_mode", ["work_mode"], False),
    ("hr_attrition", "idx_hr_attrition_hire_date", ["hire_date"], False),
    ("hr_features", "idx_hf_talent_segment", ["talent_segment"], False),
    ("hr_features", "idx_hf_country", ["country"], False),
    ("hr_features", "idx_hf_city", ["city"], False),
    ("hr_features", "idx_hf_department", ["department"], False),
    ("hr_features", "idx_hf_work_mode", ["work_mode"], False),
    ("hr_features", "idx_hf_status", ["status"], False),
    ("hr_features", "idx_hf_job_title", ["job_title"], False),
    ("hr_features", "idx_hf_sdi", ["salary_disparity_index"], False),
    (
        "hr_features",
        "idx_hf_branch_join",
        ["country", "department", "work_mode"],
        False,
    ),
    ("branch_efficiency", "idx_branch_department", ["department"], False),
    ("branch_efficiency", "idx_branch_work_mode", ["work_mode"], False),
    ("branch_efficiency", "idx_branch_turnover", ["turnover_rate_pct"], False),
]

# table, FK name, local columns, referenced table, referenced columns
FOREIGN_KEYS = [
    ("branch_efficiency", "fk_branch_country", ["country"], "dim_country", ["country"]),
    (
        "branch_efficiency",
        "fk_branch_department",
        ["department"],
        "dim_department",
        ["department"],
    ),
    (
        "branch_efficiency",
        "fk_branch_work_mode",
        ["work_mode"],
        "dim_work_mode",
        ["work_mode"],
    ),
    ("hr_features", "fk_hf_country", ["country"], "dim_country", ["country"]),
    (
        "hr_features",
        "fk_hf_department",
        ["department"],
        "dim_department",
        ["department"],
    ),
    ("hr_features", "fk_hf_work_mode", ["work_mode"], "dim_work_mode", ["work_mode"]),
    ("hr_features", "fk_hf_job_title", ["job_title"], "dim_job_title", ["job_title"]),
    ("hr_features", "fk_hf_status", ["status"], "dim_status", ["status"]),
    (
        "hr_features",
        "fk_hf_talent_segment",
        ["talent_segment"],
        "dim_talent_segment",
        ["talent_segment"],
    ),
]

EXPLAIN_QUERIES = {
    "sdi_filter": (
        "SELECT COUNT(*) AS underpaid_employees "
        "FROM hr_features WHERE salary_disparity_index < 0.9"
    ),
    "talent_segment_group": (
        "SELECT talent_segment, COUNT(*) AS n "
        "FROM hr_features GROUP BY talent_segment"
    ),
    "branch_join": (
        "SELECT COUNT(*) AS matched_rows "
        "FROM hr_features f "
        "JOIN branch_efficiency b "
        "  ON f.country = b.country "
        " AND f.department = b.department "
        " AND f.work_mode = b.work_mode"
    ),
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


def index_exists(conn, table: str, name: str) -> bool:
    return bool(
        conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND table_name = :t "
                "AND index_name = :i"
            ),
            {"t": table, "i": name},
        ).scalar_one()
    )


def fk_exists(conn, table: str, name: str) -> bool:
    return bool(
        conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.table_constraints "
                "WHERE table_schema = DATABASE() AND table_name = :t "
                "AND constraint_name = :c AND constraint_type = 'FOREIGN KEY'"
            ),
            {"t": table, "c": name},
        ).scalar_one()
    )


def pk_columns(engine: Engine, table: str) -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT column_name FROM information_schema.key_column_usage "
                "WHERE table_schema = DATABASE() AND table_name = :t "
                "AND constraint_name = 'PRIMARY' ORDER BY ordinal_position"
            ),
            {"t": table},
        ).fetchall()
    return [r[0] for r in rows]


def create_tables(engine: Engine) -> None:
    print("\n[base] Creating tables (CREATE TABLE IF NOT EXISTS)")
    with engine.begin() as conn:
        for name, ddl in DDL.items():
            conn.execute(text(ddl))
            print(f"  - {name}: ok")


def populate_dimensions(engine: Engine) -> None:
    print("\n[base] Populating dimension tables from SQL DISTINCT queries")
    with engine.begin() as conn:
        for label, sql in DIM_POPULATION:
            conn.execute(text(sql))
            # dim_country_from_branch writes to dim_country
            target = "dim_country" if label == "dim_country_from_branch" else label
            if table_exists(conn, target) and target.startswith("dim_"):
                n = conn.execute(text(f"SELECT COUNT(*) FROM {quote_ident(target)}")).scalar_one()
                print(f"  - {target:20s} {n:>8,} rows")


def apply_hr_attrition_pk(engine: Engine, apply_pk: bool, assume_yes: bool) -> None:
    """Rename the leftover CSV index to row_id and make it the PK.

    READ-ONLY unless apply_pk is True.  The exact SQL is always printed first.
    """
    print("\n[base] hr_attrition primary-key migration")
    with engine.connect() as conn:
        if not table_exists(conn, "hr_attrition"):
            print("  hr_attrition does not exist; skipping.")
            return
        columns = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = 'hr_attrition' "
                "ORDER BY ordinal_position"
            )
        ).fetchall()
        names = [r[0] for r in columns]
        leftover = next(
            (n for n in names if n.lower() in {"unnamed:_0", "unnamed: 0", "unnamed:0"}),
            None,
        )
        current_pk = pk_columns(engine, "hr_attrition")

    if current_pk:
        print(f"  Existing PRIMARY KEY: {', '.join(current_pk)}. Nothing to do.")
        return

    if leftover is None:
        proposal = (
            "ALTER TABLE hr_attrition\n"
            "  ADD COLUMN row_id INT UNSIGNED NOT NULL AUTO_INCREMENT FIRST,\n"
            "  ADD PRIMARY KEY (row_id);"
        )
    else:
        col = quote_ident(leftover)
        with engine.connect() as conn:
            _stats = conn.execute(
                text(
                    f"SELECT COUNT(*) AS total, COUNT({col}) AS non_null, "
                    f"COUNT(DISTINCT {col}) AS distinct_values "
                    f"FROM hr_attrition"
                )
            ).mappings().one()
            stats = {str(k).lower(): v for k, v in _stats.items()}
        if not (
            stats["non_null"] == stats["total"]
            and stats["distinct_values"] == stats["total"]
        ):
            print(
                f"  {leftover!r} is not unique/non-null "
                f"({stats['non_null']:,} non-null, {stats['distinct_values']:,} distinct)."
            )
            print("  Not safe as a primary key; refusing to migrate automatically.")
            return
        proposal = (
            "ALTER TABLE hr_attrition\n"
            f"  CHANGE COLUMN {col} `row_id` INT UNSIGNED NOT NULL,\n"
            "  ADD PRIMARY KEY (`row_id`),\n"
            "  ADD UNIQUE KEY `uq_hr_attrition_employee_id` (`employee_id`);"
        )

    print("  SQL to execute:")
    for line in proposal.splitlines():
        print("    " + line)

    if not apply_pk:
        print("  NOT APPLIED. Re-run with --apply-pk (and --yes) after approval.")
        return

    if not assume_yes:
        answer = input("  Type YES to execute the statement above: ").strip()
        if answer != "YES":
            print("  Aborted by operator.")
            return

    start = time.perf_counter()
    with engine.begin() as conn:
        conn.execute(text(proposal))
    print(f"  APPLIED in {time.perf_counter() - start:.1f}s")


def missing_indexes(engine: Engine) -> list[tuple]:
    missing = []
    with engine.connect() as conn:
        for table, name, cols, unique in INDEXES:
            if table_exists(conn, table) and not index_exists(conn, table, name):
                missing.append((table, name, cols, unique))
    return missing


def ensure_indexes(engine: Engine) -> None:
    print("\n[indexes] Ensuring secondary indexes")
    with engine.begin() as conn:
        for table, name, cols, unique in INDEXES:
            if not table_exists(conn, table):
                print(f"  - {table}: table missing, skipped")
                continue
            if index_exists(conn, table, name):
                print(f"  = {table}.{name}: already exists")
                continue
            col_sql = ", ".join(quote_ident(c) for c in cols)
            unique_sql = "UNIQUE " if unique else ""
            ddl = (
                f"ALTER TABLE {quote_ident(table)} "
                f"ADD {unique_sql}INDEX {quote_ident(name)} ({col_sql})"
            )
            conn.execute(text(ddl))
            print(f"  + {table}.{name} ({col_sql})")


def ensure_foreign_keys(engine: Engine) -> None:
    print("\n[indexes] Ensuring foreign keys")
    with engine.begin() as conn:
        for table, name, cols, ref_table, ref_cols in FOREIGN_KEYS:
            if not table_exists(conn, table) or not table_exists(conn, ref_table):
                print(f"  - {name}: table missing, skipped")
                continue
            if fk_exists(conn, table, name):
                print(f"  = {name}: already exists")
                continue
            col_sql = ", ".join(quote_ident(c) for c in cols)
            ref_sql = ", ".join(quote_ident(c) for c in ref_cols)
            ddl = (
                f"ALTER TABLE {quote_ident(table)} "
                f"ADD CONSTRAINT {quote_ident(name)} FOREIGN KEY ({col_sql}) "
                f"REFERENCES {quote_ident(ref_table)} ({ref_sql})"
            )
            conn.execute(text(ddl))
            print(f"  + {name}: {table}({col_sql}) -> {ref_table}({ref_sql})")


def _walk_plan(node):
    if isinstance(node, dict):
        if "table_name" in node and "access_type" in node:
            yield node
        for value in node.values():
            yield from _walk_plan(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_plan(value)


def capture_explain(engine: Engine, label: str) -> dict:
    print(f"\n[indexes] EXPLAIN ({label})")
    result = {}
    with engine.connect() as conn:
        for name, sql in EXPLAIN_QUERIES.items():
            raw = conn.execute(text("EXPLAIN FORMAT=JSON " + sql)).scalar_one()
            plan = json.loads(raw) if isinstance(raw, str) else raw
            result[name] = {"query": sql, "plan": plan}
            summary = []
            for table in _walk_plan(plan):
                summary.append(
                    f"{table.get('table_name')}: "
                    f"access={table.get('access_type')} "
                    f"key={table.get('key')} "
                    f"rows={table.get('rows_examined_per_scan')}"
                )
            print(f"  - {name}: " + ("; ".join(summary) if summary else "no table node"))
    return result


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {path}")


def run_base(engine: Engine, apply_pk: bool, assume_yes: bool) -> None:
    create_tables(engine)
    apply_hr_attrition_pk(engine, apply_pk=apply_pk, assume_yes=assume_yes)
    populate_dimensions(engine)
    if not pk_columns(engine, "hr_attrition"):
        print(
            "\nWARNING: hr_attrition still has no PRIMARY KEY. "
            "Task 4 requires one; re-run with --apply-pk after approval."
        )


def run_indexes(engine: Engine) -> None:
    populate_dimensions(engine)

    pending = missing_indexes(engine)
    before = None
    if pending:
        print(f"\n[indexes] {len(pending)} index(es) missing; capturing BEFORE plans")
        before = capture_explain(engine, "before indexing")
    else:
        print("\n[indexes] All indexes already exist; only capturing AFTER plans")

    ensure_indexes(engine)
    ensure_foreign_keys(engine)
    after = capture_explain(engine, "after indexing")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if before is not None:
        write_json(OUTPUT_DIR / "explain_before.json", before)
    write_json(OUTPUT_DIR / "explain_after.json", after)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=["base", "indexes", "all"],
        default="base",
        help="base = tables/dims; indexes = indexes/FKs/EXPLAIN; all = both",
    )
    parser.add_argument(
        "--apply-pk",
        action="store_true",
        help="apply the approved hr_attrition primary-key ALTER",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="skip the interactive YES prompt (use only after explicit approval)",
    )
    args = parser.parse_args()

    engine = get_engine()
    try:
        with engine.connect() as conn:
            print(f"Connected to {conn.execute(text('SELECT DATABASE()')).scalar_one()}")
    except Exception as exc:  # noqa: BLE001 - friendly startup error
        print(f"Could not connect to MySQL: {exc}", file=sys.stderr)
        return 1

    if args.phase in {"base", "all"}:
        run_base(engine, apply_pk=args.apply_pk, assume_yes=args.yes)
    if args.phase in {"indexes", "all"}:
        run_indexes(engine)

    print("\nSchema phase complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
