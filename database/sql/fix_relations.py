"""Inspect, validate, and add the missing hr_features foreign keys.

Usage
-----
    python fix_relations.py --dry-run     # Steps 1-2 + planned ALTERs only
    python fix_relations.py               # Steps 1-5, asks YES before each change
    python fix_relations.py --yes         # Steps 1-5 without prompts (only after
                                          # the operator has approved the plan)

The script never drops/recreates a table and never changes hr_attrition columns.
It is idempotent: existing constraints/indexes are detected and skipped.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from config import get_engine, quote_ident

SQL_DIR = Path(__file__).resolve().parent
REPORT_PATH = SQL_DIR / "relations_report.md"

FK_SPECS = [
    {
        "name": "fk_hf_job_title",
        "child": "hr_features",
        "child_col": "job_title",
        "parent": "dim_job_title",
        "parent_col": "job_title",
    },
    {
        "name": "fk_hf_status",
        "child": "hr_features",
        "child_col": "status",
        "parent": "dim_status",
        "parent_col": "status",
    },
    {
        "name": "fk_hf_work_mode",
        "child": "hr_features",
        "child_col": "work_mode",
        "parent": "dim_work_mode",
        "parent_col": "work_mode",
    },
    {
        "name": "fk_hf_talent_segment",
        "child": "hr_features",
        "child_col": "talent_segment",
        "parent": "dim_talent_segment",
        "parent_col": "talent_segment",
    },
    {
        "name": "fk_hf_attrition",
        "child": "hr_features",
        "child_col": "employee_id",
        "parent": "hr_attrition",
        "parent_col": "employee_id",
    },
]

# The five FKs described as already present in the task brief.
EXPECTED_CURRENT_FKS = [
    ("branch_efficiency", "country", "dim_country", "country"),
    ("branch_efficiency", "department", "dim_department", "department"),
    ("branch_efficiency", "work_mode", "dim_work_mode", "work_mode"),
    ("hr_features", "country", "dim_country", "country"),
    ("hr_features", "department", "dim_department", "department"),
]

DIM_SPECS = [
    ("dim_country", "country", "hr_features", "country"),
    ("dim_department", "department", "hr_features", "department"),
    ("dim_job_title", "job_title", "hr_features", "job_title"),
    ("dim_work_mode", "work_mode", "hr_features", "work_mode"),
    ("dim_status", "status", "hr_features", "status"),
    ("dim_talent_segment", "talent_segment", "hr_features", "talent_segment"),
]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records", date_format="iso"))


def confirm(sql: str, assume_yes: bool) -> bool:
    print("\nPlanned statement:")
    for line in sql.strip().splitlines():
        print("  " + line)
    if assume_yes:
        print("  --yes supplied: executing.")
        return True
    answer = input("  Type YES to execute, anything else to skip: ").strip()
    return answer == "YES"


def check_no_concurrent_ddl(engine: Engine) -> bool:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT ID, TIME, INFO FROM information_schema.processlist "
                "WHERE DB = DATABASE() AND INFO LIKE 'ALTER TABLE%' "
                "AND ID <> CONNECTION_ID()"
            )
        ).mappings().all()
    if rows:
        print("Another ALTER is already running. Wait for it to finish:")
        for row in rows:
            print(f"  id={row['ID']} time={row['TIME']}s {str(row['INFO'])[:120]}")
        return False
    return True


def list_foreign_keys(engine: Engine) -> list[dict]:
    sql = """
        SELECT k.CONSTRAINT_NAME,
               k.TABLE_NAME,
               k.COLUMN_NAME,
               k.REFERENCED_TABLE_NAME,
               k.REFERENCED_COLUMN_NAME,
               r.UPDATE_RULE,
               r.DELETE_RULE
        FROM information_schema.KEY_COLUMN_USAGE k
        LEFT JOIN information_schema.REFERENTIAL_CONSTRAINTS r
               ON r.CONSTRAINT_SCHEMA = k.CONSTRAINT_SCHEMA
              AND r.CONSTRAINT_NAME = k.CONSTRAINT_NAME
        WHERE k.TABLE_SCHEMA = DATABASE()
          AND k.REFERENCED_TABLE_NAME IS NOT NULL
        ORDER BY k.TABLE_NAME, k.CONSTRAINT_NAME, k.ORDINAL_POSITION
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn).rename(columns=str.lower)
    return records(df)


def get_tables(engine: Engine) -> list[str]:
    with engine.connect() as conn:
        df = pd.read_sql(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE' "
                "ORDER BY table_name"
            ),
            conn,
        ).rename(columns=str.lower)
    return df["table_name"].tolist()


def table_counts(engine: Engine) -> dict[str, int]:
    counts = {}
    with engine.connect() as conn:
        for table in get_tables(engine):
            counts[table] = conn.execute(
                text(f"SELECT COUNT(*) FROM {quote_ident(table)}")
            ).scalar_one()
    return counts


def column_meta(engine: Engine, table: str, column: str) -> dict:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, DATA_TYPE, "
                "CHARACTER_MAXIMUM_LENGTH, CHARACTER_SET_NAME, COLLATION_NAME, "
                "IS_NULLABLE "
                "FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = :t AND COLUMN_NAME = :c"
            ),
            {"t": table, "c": column},
        ).mappings().one()
    return {str(k).lower(): v for k, v in row.items()}


def foreign_key_exists(engine: Engine, name: str) -> bool:
    with engine.connect() as conn:
        return bool(
            conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.table_constraints "
                    "WHERE table_schema = DATABASE() AND constraint_name = :n "
                    "AND constraint_type = 'FOREIGN KEY'"
                ),
                {"n": name},
            ).scalar_one()
        )


def index_exists(engine: Engine, table: str, column: str) -> bool:
    with engine.connect() as conn:
        return bool(
            conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.statistics "
                    "WHERE table_schema = DATABASE() AND table_name = :t "
                    "AND column_name = :c AND seq_in_index = 1"
                ),
                {"t": table, "c": column},
            ).scalar_one()
        )


def orphan_info(engine: Engine, spec: dict) -> dict:
    child = quote_ident(spec["child"])
    parent = quote_ident(spec["parent"])
    ccol = quote_ident(spec["child_col"])
    pcol = quote_ident(spec["parent_col"])
    join = f"{child} c LEFT JOIN {parent} p ON c.{ccol} = p.{pcol}"
    where = f"c.{ccol} IS NOT NULL AND p.{pcol} IS NULL"

    with engine.connect() as conn:
        count = conn.execute(
            text(f"SELECT COUNT(*) FROM {join} WHERE {where}")
        ).scalar_one()
        samples = conn.execute(
            text(f"SELECT DISTINCT c.{ccol} FROM {join} WHERE {where} LIMIT 5")
        ).fetchall()
    return {
        "fk": spec["name"],
        "child": f"{spec['child']}.{spec['child_col']}",
        "parent": f"{spec['parent']}.{spec['parent_col']}",
        "orphans": int(count),
        "samples": [str(r[0]) for r in samples],
    }


def employee_id_health(engine: Engine) -> dict:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT COUNT(*) AS total, "
                "COUNT(employee_id) AS non_null, "
                "COUNT(DISTINCT employee_id) AS distinct_values "
                "FROM hr_attrition"
            )
        ).mappings().one()
    data = {str(k).lower(): int(v) for k, v in row.items()}
    data["nulls"] = data["total"] - data["non_null"]
    data["duplicates"] = data["non_null"] - data["distinct_values"]
    return data


# --------------------------------------------------------------------------- #
# Step 1 - inspection
# --------------------------------------------------------------------------- #
def step1_inspect(engine: Engine) -> dict:
    print("=" * 78)
    print("Step 1 - inspect existing foreign keys, row counts, column types")
    print("=" * 78)

    fks = list_foreign_keys(engine)
    print("\nExisting foreign keys:")
    if not fks:
        print("  (none)")
    for fk in fks:
        print(
            f"  {fk['table_name']}.{fk['column_name']} -> "
            f"{fk['referenced_table_name']}.{fk['referenced_column_name']} "
            f"[{fk['constraint_name']}] "
            f"ON UPDATE {fk['update_rule']} ON DELETE {fk['delete_rule']}"
        )

    current_keys = {
        (f["table_name"], f["column_name"], f["referenced_table_name"], f["referenced_column_name"])
        for f in fks
    }
    expected_keys = set(EXPECTED_CURRENT_FKS)
    print("\nDifference from the brief's 'current state' (5 FKs):")
    missing = expected_keys - current_keys
    extra = current_keys - expected_keys
    if not missing and not extra:
        print("  exactly the 5 expected FKs are present")
    for item in sorted(missing):
        print(f"  MISSING vs brief: {item[0]}.{item[1]} -> {item[2]}.{item[3]}")
    for item in sorted(extra):
        print(f"  ALREADY PRESENT (beyond brief): {item[0]}.{item[1]} -> {item[2]}.{item[3]}")

    counts = table_counts(engine)
    print("\nRow counts:")
    for table, count in counts.items():
        print(f"  {table:24s} {count:>12,}")
    hr = counts.get("hr_attrition")
    hf = counts.get("hr_features")
    if hr is not None and hf is not None:
        if hf == hr:
            print(f"\n  hr_features == hr_attrition ({hf:,}): relationship is 1 : 1")
        elif hf < hr:
            print(
                f"\n  hr_features ({hf:,}) < hr_attrition ({hr:,}): "
                "relationship is 1 : 0..1 (some raw employees have no feature row)"
            )
        else:
            print(
                f"\n  hr_features ({hf:,}) > hr_attrition ({hr:,}): "
                "unexpected; investigate before adding the employee_id FK"
            )

    print("\nColumn compatibility for the five target FKs:")
    compat = []
    for spec in FK_SPECS:
        child = column_meta(engine, spec["child"], spec["child_col"])
        parent = column_meta(engine, spec["parent"], spec["parent_col"])
        hard = (
            child["character_set_name"] != parent["character_set_name"]
            or child["collation_name"] != parent["collation_name"]
            or (
                child["data_type"] != parent["data_type"]
                and {child["data_type"], parent["data_type"]} != {"char", "varchar"}
            )
        )
        soft = (
            child["data_type"] != parent["data_type"]
            or child["character_maximum_length"] != parent["character_maximum_length"]
        )
        status = "OK" if not hard and not soft else ("SOFT-WARN" if not hard else "HARD-FAIL")
        entry = {
            "name": spec["name"],
            "child": spec["child"],
            "child_col": spec["child_col"],
            "parent": spec["parent"],
            "parent_col": spec["parent_col"],
            "child_type": child["column_type"],
            "parent_type": parent["column_type"],
            "child_charset": child["character_set_name"],
            "parent_charset": parent["character_set_name"],
            "child_collation": child["collation_name"],
            "parent_collation": parent["collation_name"],
            "status": status,
            "hard": hard,
            "soft": soft,
        }
        compat.append(entry)
        print(
            f"  {spec['name']:24s} {status:9s} "
            f"{child['column_type']} ({child['collation_name']}) -> "
            f"{parent['column_type']} ({parent['collation_name']})"
        )
        if soft and not hard:
            print("      note: type/length differs but both are string types; MySQL may accept it.")
        if hard:
            print("      note: charset/collation/type mismatch must be fixed before adding the FK.")

    return {
        "fks": fks,
        "current_keys": current_keys,
        "counts": counts,
        "compat": compat,
    }


# --------------------------------------------------------------------------- #
# Step 2 - data integrity
# --------------------------------------------------------------------------- #
def step2_integrity(engine: Engine, compat: list[dict]) -> dict:
    print("\n" + "=" * 78)
    print("Step 2 - data integrity (read-only)")
    print("=" * 78)

    orphans = []
    print("\nOrphan checks:")
    print(f"  {'FK':24s} {'orphans':>9s}  sample orphan values")
    for spec in FK_SPECS:
        info = orphan_info(engine, spec)
        orphans.append(info)
        samples = ", ".join(info["samples"][:5]) if info["samples"] else "-"
        print(f"  {info['fk']:24s} {info['orphans']:>9,}  {samples}")

    health = employee_id_health(engine)
    print("\nhr_attrition.employee_id health:")
    print(
        f"  total={health['total']:,}  non_null={health['non_null']:,}  "
        f"nulls={health['nulls']:,}  duplicates={health['duplicates']:,}  "
        f"distinct={health['distinct_values']:,}"
    )

    print("\nDimension quality checks:")
    quality = []
    for dim, dim_col, fact, fact_col in DIM_SPECS:
        with engine.connect() as conn:
            dim_count = conn.execute(
                text(f"SELECT COUNT(*) FROM {quote_ident(dim)}")
            ).scalar_one()
            dim_ws = conn.execute(
                text(
                    f"SELECT COUNT(*) FROM {quote_ident(dim)} "
                    f"WHERE {quote_ident(dim_col)} <> TRIM({quote_ident(dim_col)})"
                )
            ).scalar_one()
            fact_ws = conn.execute(
                text(
                    f"SELECT COUNT(*) FROM {quote_ident(fact)} "
                    f"WHERE {quote_ident(fact_col)} <> TRIM({quote_ident(fact_col)})"
                )
            ).scalar_one()
            case_mismatch = conn.execute(
                text(
                    f"SELECT COUNT(*) FROM {quote_ident(fact)} f "
                    f"JOIN {quote_ident(dim)} d ON f.{quote_ident(fact_col)} = d.{quote_ident(dim_col)} "
                    f"WHERE BINARY f.{quote_ident(fact_col)} <> BINARY d.{quote_ident(dim_col)}"
                )
            ).scalar_one()
            case_samples = conn.execute(
                text(
                    f"SELECT DISTINCT f.{quote_ident(fact_col)} AS fact_value, "
                    f"d.{quote_ident(dim_col)} AS dim_value "
                    f"FROM {quote_ident(fact)} f "
                    f"JOIN {quote_ident(dim)} d ON f.{quote_ident(fact_col)} = d.{quote_ident(dim_col)} "
                    f"WHERE BINARY f.{quote_ident(fact_col)} <> BINARY d.{quote_ident(dim_col)} "
                    f"LIMIT 5"
                )
            ).fetchall()
        samples = ", ".join(f"{r[0]!r} vs {r[1]!r}" for r in case_samples) or "-"
        quality.append(
            {
                "dim": dim,
                "dim_col": dim_col,
                "dim_count": int(dim_count),
                "dim_whitespace": int(dim_ws),
                "fact_whitespace": int(fact_ws),
                "case_mismatch": int(case_mismatch),
                "samples": samples,
            }
        )
        print(
            f"  {dim:22s} rows={dim_count:>5,}  dim_ws={dim_ws:>5,}  "
            f"fact_ws={fact_ws:>6,}  case_mismatch={case_mismatch:>6,}  {samples}"
        )

    return {
        "orphans": orphans,
        "employee_health": health,
        "quality": quality,
        "compat": compat,
    }


# --------------------------------------------------------------------------- #
# Step 3 - propose/apply fixes
# --------------------------------------------------------------------------- #
def propose_fixes(engine: Engine, integrity: dict) -> list[dict]:
    fixes = []

    # Missing dimension values (orphans whose parent is a dim_* table).
    for orphan in integrity["orphans"]:
        parent_table, parent_col = orphan["parent"].split(".", 1)
        child_table, child_col = orphan["child"].split(".", 1)
        if not parent_table.startswith("dim_") or orphan["orphans"] == 0:
            continue
        sql = (
            f"INSERT IGNORE INTO {quote_ident(parent_table)} ({quote_ident(parent_col)})\n"
            f"SELECT DISTINCT f.{quote_ident(child_col)}\n"
            f"FROM {quote_ident(child_table)} f\n"
            f"LEFT JOIN {quote_ident(parent_table)} d "
            f"ON f.{quote_ident(child_col)} = d.{quote_ident(parent_col)}\n"
            f"WHERE f.{quote_ident(child_col)} IS NOT NULL\n"
            f"  AND d.{quote_ident(parent_col)} IS NULL"
        )
        fixes.append(
            {
                "kind": "insert_dim",
                "description": (
                    f"Add {orphan['orphans']:,} missing value(s) to "
                    f"{parent_table}.{parent_col}"
                ),
                "sql": sql,
            }
        )

    # Whitespace in dimension tables.
    for q in integrity["quality"]:
        if q["dim_whitespace"]:
            sql = (
                f"UPDATE {quote_ident(q['dim'])}\n"
                f"SET {quote_ident(q['dim_col'])} = TRIM({quote_ident(q['dim_col'])})\n"
                f"WHERE {quote_ident(q['dim_col'])} <> TRIM({quote_ident(q['dim_col'])})"
            )
            fixes.append(
                {
                    "kind": "trim_dim",
                    "description": (
                        f"Trim {q['dim_whitespace']:,} whitespace-padded value(s) in {q['dim']}"
                    ),
                    "sql": sql,
                }
            )
        if q["fact_whitespace"]:
            # Find the fact table/column from DIM_SPECS.
            spec = next(s for s in DIM_SPECS if s[0] == q["dim"])
            fact, fact_col = spec[2], spec[3]
            sql = (
                f"UPDATE {quote_ident(fact)}\n"
                f"SET {quote_ident(fact_col)} = TRIM({quote_ident(fact_col)})\n"
                f"WHERE {quote_ident(fact_col)} <> TRIM({quote_ident(fact_col)})"
            )
            fixes.append(
                {
                    "kind": "trim_fact",
                    "description": (
                        f"Trim {q['fact_whitespace']:,} whitespace-padded value(s) in "
                        f"{fact}.{fact_col}"
                    ),
                    "sql": sql,
                }
            )

    # Case-only differences: align the fact value to the dimension's canonical value.
    for q in integrity["quality"]:
        if q["case_mismatch"]:
            spec = next(s for s in DIM_SPECS if s[0] == q["dim"])
            fact, fact_col = spec[2], spec[3]
            sql = (
                f"UPDATE {quote_ident(fact)} f\n"
                f"JOIN {quote_ident(q['dim'])} d "
                f"ON f.{quote_ident(fact_col)} = d.{quote_ident(q['dim_col'])}\n"
                f"SET f.{quote_ident(fact_col)} = d.{quote_ident(q['dim_col'])}\n"
                f"WHERE BINARY f.{quote_ident(fact_col)} <> BINARY d.{quote_ident(q['dim_col'])}"
            )
            fixes.append(
                {
                    "kind": "case_fact",
                    "description": (
                        f"Align {q['case_mismatch']:,} case-only difference(s) in "
                        f"{fact}.{fact_col} to {q['dim']}"
                    ),
                    "sql": sql,
                }
            )

    # Type/collation mismatches: propose child-side ALTER only.
    for c in integrity["compat"]:
        if not c["hard"]:
            continue
        sql = (
            f"ALTER TABLE {quote_ident(c['child'])}\n"
            f"  MODIFY COLUMN {quote_ident(c['child_col'])} "
            f"{c['parent_type']} NOT NULL"
        )
        fixes.append(
            {
                "kind": "alter_compat",
                "description": (
                    f"Align {c['child']}.{c['child_col']} with "
                    f"{c['parent']}.{c['parent_col']} (charset/collation/type)"
                ),
                "sql": sql,
            }
        )

    return fixes


def apply_fixes(engine: Engine, fixes: list[dict], dry_run: bool, assume_yes: bool) -> list[dict]:
    print("\n" + "=" * 78)
    print("Step 3 - proposed fixes")
    print("=" * 78)
    if not fixes:
        print("  No fixes needed.")
        return []

    results = []
    for fix in fixes:
        print(f"\n  {fix['description']}")
        print("  SQL:")
        for line in fix["sql"].splitlines():
            print("    " + line)
        if dry_run:
            results.append({**fix, "status": "PLANNED (dry-run)"})
            continue
        if not confirm(fix["sql"], assume_yes):
            results.append({**fix, "status": "SKIPPED (not confirmed)"})
            continue
        started = time.perf_counter()
        try:
            with engine.begin() as conn:
                result = conn.execute(text(fix["sql"]))
                affected = result.rowcount
            elapsed = time.perf_counter() - started
            print(f"  APPLIED in {elapsed:.1f}s, affected={affected:,}")
            results.append({**fix, "status": f"APPLIED ({affected:,} rows, {elapsed:.1f}s)"})
        except Exception as exc:  # noqa: BLE001 - print exact DB error
            elapsed = time.perf_counter() - started
            print(f"  FAILED after {elapsed:.1f}s: {exc}")
            results.append({**fix, "status": f"FAILED: {exc}"})
    return results


# --------------------------------------------------------------------------- #
# Step 4 - add foreign keys
# --------------------------------------------------------------------------- #
def step4_add_fks(
    engine: Engine,
    compat: list[dict],
    dry_run: bool,
    assume_yes: bool,
) -> list[dict]:
    print("\n" + "=" * 78)
    print("Step 4 - add missing foreign keys")
    print("=" * 78)

    compat_by_name = {c["name"]: c for c in compat}
    results = []

    for spec in FK_SPECS:
        name = spec["name"]
        info = compat_by_name[name]
        print(f"\n  {name}: {spec['child']}.{spec['child_col']} -> "
              f"{spec['parent']}.{spec['parent_col']}")

        if foreign_key_exists(engine, name):
            print("  already exists; skipping.")
            results.append({"name": name, "status": "ALREADY EXISTS", "elapsed": 0.0})
            continue

        if info["hard"]:
            print("  skipped: hard type/charset/collation mismatch (see Step 1).")
            results.append(
                {"name": name, "status": "SKIPPED (type/collation mismatch)", "elapsed": 0.0}
            )
            continue

        orphan = orphan_info(engine, spec)
        if orphan["orphans"]:
            print(f"  skipped: {orphan['orphans']:,} orphan row(s) remain.")
            results.append(
                {
                    "name": name,
                    "status": f"SKIPPED ({orphan['orphans']:,} orphans)",
                    "elapsed": 0.0,
                }
            )
            continue

        if spec["child_col"] == "employee_id":
            health = employee_id_health(engine)
            if health["nulls"] or health["duplicates"]:
                print(
                    f"  skipped: parent employee_id has nulls={health['nulls']:,}, "
                    f"duplicates={health['duplicates']:,}."
                )
                results.append(
                    {"name": name, "status": "SKIPPED (parent not unique)", "elapsed": 0.0}
                )
                continue
            print("  WARNING: this FK validates 2,000,000 rows and can take several minutes.")

        index_ok = index_exists(engine, spec["child"], spec["child_col"])
        if not index_ok:
            print(
                f"  note: no index on {spec['child']}.{spec['child_col']}; "
                "MySQL will create one for the FK automatically."
            )

        sql = (
            f"ALTER TABLE {quote_ident(spec['child'])}\n"
            f"  ADD CONSTRAINT {quote_ident(name)}\n"
            f"  FOREIGN KEY ({quote_ident(spec['child_col'])})\n"
            f"  REFERENCES {quote_ident(spec['parent'])} ({quote_ident(spec['parent_col'])})\n"
            "  ON UPDATE CASCADE\n"
            "  ON DELETE RESTRICT"
        )

        if dry_run:
            print("  PLANNED (dry-run):")
            for line in sql.splitlines():
                print("    " + line)
            results.append({"name": name, "status": "PLANNED (dry-run)", "elapsed": 0.0})
            continue

        if not confirm(sql, assume_yes):
            results.append({"name": name, "status": "SKIPPED (not confirmed)", "elapsed": 0.0})
            continue

        started = time.perf_counter()
        try:
            with engine.begin() as conn:
                conn.execute(text(sql))
            elapsed = time.perf_counter() - started
            print(f"  ADDED in {elapsed:.1f}s")
            results.append({"name": name, "status": "ADDED", "elapsed": elapsed})
        except Exception as exc:  # noqa: BLE001 - exact MySQL error is required
            elapsed = time.perf_counter() - started
            print(f"  FAILED after {elapsed:.1f}s")
            print(f"  exact error: {exc}")
            cause = explain_fk_error(exc)
            print(f"  cause: {cause}")
            results.append(
                {
                    "name": name,
                    "status": f"FAILED: {exc}",
                    "elapsed": elapsed,
                    "cause": cause,
                }
            )
            if "3780" in str(exc) or "incompatible" in str(exc).lower():
                print("  proposed child-side fix (not executed):")
                print(
                    f"    ALTER TABLE {quote_ident(spec['child'])} "
                    f"MODIFY COLUMN {quote_ident(spec['child_col'])} "
                    f"{info['parent_type']} NOT NULL;"
                )
    return results


def explain_fk_error(exc: Exception) -> str:
    text_err = str(exc).lower()
    if "3780" in text_err or "incompatible" in text_err:
        return "Child and parent columns differ in type/charset/collation."
    if "1452" in text_err or "foreign key constraint fails" in text_err:
        return "At least one child value has no matching parent value (orphan rows)."
    if "1822" in text_err or "missing index" in text_err:
        return "The referenced parent column is not indexed."
    if "1215" in text_err:
        return "The constraint cannot be added (often a referenced-index/type problem)."
    return "MySQL rejected the constraint; see the exact error above."


# --------------------------------------------------------------------------- #
# Step 5 - verify
# --------------------------------------------------------------------------- #
def step5_verify(engine: Engine) -> dict:
    print("\n" + "=" * 78)
    print("Step 5 - verify")
    print("=" * 78)

    fks = list_foreign_keys(engine)
    print(f"\nForeign keys now present: {len(fks)} (expected 10)")
    for fk in fks:
        print(
            f"  {fk['table_name']}.{fk['column_name']} -> "
            f"{fk['referenced_table_name']}.{fk['referenced_column_name']} "
            f"[{fk['constraint_name']}] "
            f"ON UPDATE {fk['update_rule']} ON DELETE {fk['delete_rule']}"
        )

    join_sql = """
        SELECT d.talent_segment,
               COUNT(*) AS employees
        FROM hr_features f
        JOIN dim_talent_segment d
          ON f.talent_segment = d.talent_segment
        JOIN hr_attrition a
          ON f.employee_id = a.employee_id
        GROUP BY d.talent_segment
        ORDER BY employees DESC
    """

    print("\nJOIN proof (hr_features + dim_talent_segment + hr_attrition):")
    started = time.perf_counter()
    with engine.connect() as conn:
        df = pd.read_sql(text(join_sql), conn).rename(columns=str.lower)
        elapsed = time.perf_counter() - started
        print(df.to_string(index=False))
        print(f"\nExecution time: {elapsed:.3f}s")

        explain = pd.read_sql(text("EXPLAIN " + join_sql), conn).rename(columns=str.lower)
        print("\nEXPLAIN:")
        print(explain.to_string(index=False))

    return {
        "fks": fks,
        "join_rows": records(df),
        "join_elapsed": elapsed,
        "explain": records(explain),
    }


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def write_report(
    before: dict,
    integrity: dict,
    fixes: list[dict],
    add_results: list[dict],
    verify: dict,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Relations report",
        "",
        f"Generated: `{now}`",
        "",
        "## Before",
        "",
        f"- Foreign keys present: **{len(before['fks'])}**",
        "- The brief described 5 FKs; any additional ones were added by the earlier "
        "`create_schema.py --phase indexes` run and are listed below.",
        "",
        "| child.column | parent.column | constraint | ON UPDATE | ON DELETE |",
        "|---|---|---|---|---|",
    ]
    for fk in before["fks"]:
        lines.append(
            f"| {fk['table_name']}.{fk['column_name']} | "
            f"{fk['referenced_table_name']}.{fk['referenced_column_name']} | "
            f"`{fk['constraint_name']}` | {fk['update_rule']} | {fk['delete_rule']} |"
        )

    lines += ["", "## Row counts", "", "| table | rows |", "|---|---:|"]
    for table, count in before["counts"].items():
        lines.append(f"| {table} | {count:,} |")

    hr = before["counts"].get("hr_attrition")
    hf = before["counts"].get("hr_features")
    if hr is not None and hf is not None:
        lines += [
            "",
            f"- `hr_features` = **{hf:,}**, `hr_attrition` = **{hr:,}** → "
            + ("1 : 1" if hf == hr else "1 : 0..1"),
        ]

    lines += [
        "",
        "## Column compatibility",
        "",
        "| FK | child type | parent type | status |",
        "|---|---|---|---|",
    ]
    for c in before["compat"]:
        lines.append(
            f"| `{c['name']}` | `{c['child_type']}` ({c['child_collation']}) | "
            f"`{c['parent_type']}` ({c['parent_collation']}) | {c['status']} |"
        )

    lines += [
        "",
        "## Orphan checks (Step 2)",
        "",
        "| FK | child.column | parent.column | orphan rows | sample values |",
        "|---|---|---|---:|---|",
    ]
    for o in integrity["orphans"]:
        sample = ", ".join(o["samples"][:5]) if o["samples"] else "-"
        lines.append(
            f"| `{o['fk']}` | `{o['child']}` | `{o['parent']}` | "
            f"{o['orphans']:,} | {sample} |"
        )

    hp = integrity["employee_health"]
    lines += [
        "",
        "### hr_attrition.employee_id health",
        "",
        f"- total: {hp['total']:,}",
        f"- non-null: {hp['non_null']:,}",
        f"- nulls: {hp['nulls']:,}",
        f"- duplicates: {hp['duplicates']:,}",
        f"- distinct: {hp['distinct_values']:,}",
        "",
        "## Dimension quality checks",
        "",
        "| dim | rows | dim whitespace | fact whitespace | case mismatch | samples |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for q in integrity["quality"]:
        lines.append(
            f"| `{q['dim']}` | {q['dim_count']:,} | {q['dim_whitespace']:,} | "
            f"{q['fact_whitespace']:,} | {q['case_mismatch']:,} | {q['samples']} |"
        )

    lines += ["", "## Fixes (Step 3)", ""]
    if not fixes:
        lines.append("No fixes were needed.")
    else:
        lines += ["| description | status |", "|---|---|"]
        for fix in fixes:
            lines.append(f"| {fix['description']} | {fix.get('status', 'proposed')} |")

    lines += [
        "",
        "## Foreign keys added (Step 4)",
        "",
        "| constraint | status | elapsed |",
        "|---|---|---:|",
    ]
    for r in add_results:
        lines.append(f"| `{r['name']}` | {r['status']} | {r['elapsed']:.1f}s |")

    lines += [
        "",
        "## After (Step 5)",
        "",
        f"- Foreign keys present: **{len(verify['fks'])}** (expected 10)",
        "",
        "| child.column | parent.column | constraint |",
        "|---|---|---|",
    ]
    for fk in verify["fks"]:
        lines.append(
            f"| {fk['table_name']}.{fk['column_name']} | "
            f"{fk['referenced_table_name']}.{fk['referenced_column_name']} | "
            f"`{fk['constraint_name']}` |"
        )

    lines += [
        "",
        "### JOIN proof",
        "",
        f"Execution time: **{verify['join_elapsed']:.3f}s**",
        "",
        "| talent_segment | employees |",
        "|---|---:|",
    ]
    for row in verify["join_rows"]:
        lines.append(f"| {row['talent_segment']} | {row['employees']:,} |")

    lines += ["", "### EXPLAIN", "", "```"]
    for row in verify["explain"]:
        lines.append(str(row))
    lines += ["```", ""]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {REPORT_PATH}")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run only Steps 1-2 and print planned ALTER statements",
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
    except Exception as exc:  # noqa: BLE001
        print(f"Could not connect to MySQL: {exc}", file=sys.stderr)
        return 1

    if not check_no_concurrent_ddl(engine):
        return 1

    before = step1_inspect(engine)
    integrity = step2_integrity(engine, before["compat"])

    fixes = propose_fixes(engine, integrity)
    fix_results = apply_fixes(engine, fixes, dry_run=args.dry_run, assume_yes=args.yes)

    add_results = step4_add_fks(
        engine,
        before["compat"],
        dry_run=args.dry_run,
        assume_yes=args.yes,
    )

    if args.dry_run:
        print("\n" + "=" * 78)
        print("Dry-run finished. No schema changes were made.")
        print("Planned ALTER statements were printed above.")
        print("=" * 78)
        return 0

    verify = step5_verify(engine)
    write_report(before, integrity, fix_results, add_results, verify)

    expected = 10
    ok = len(verify["fks"]) == expected
    unresolved = [o for o in integrity["orphans"] if o["orphans"]]
    if unresolved:
        print("\nUnresolved orphan rows remain; see relations_report.md.")
    print("\nRelations:", "PASS" if ok else f"INCOMPLETE ({len(verify['fks'])}/{expected} FKs)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
