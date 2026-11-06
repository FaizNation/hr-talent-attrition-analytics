"""Task 1: verify the existing hr_attrition table (READ-ONLY).

This script never executes ALTER/DROP/DELETE.  It prints the exact DDL that
would be needed to give hr_attrition a primary key, so the operator can approve
it explicitly.
"""
from __future__ import annotations

import sys

import pandas as pd
from sqlalchemy import text

from config import DB_HOST, DB_NAME, DB_PORT, DB_USER, get_engine, quote_ident

EXPECTED_ROWS = 2_000_000
LEFT_OVER_NAMES = {"unnamed:_0", "unnamed: 0", "unnamed:0"}


def main() -> int:
    engine = get_engine()
    ok = True

    print("=" * 78)
    print("Task 1 - verify hr_attrition")
    print("=" * 78)
    print(f"Server : {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

    with engine.connect() as conn:
        version = conn.execute(text("SELECT VERSION()")).scalar_one()
        print(f"MySQL  : {version}")

        tables = pd.read_sql(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = DATABASE() ORDER BY table_name"
            ),
            conn,
        ).rename(columns=str.lower)
        print("\nTables in schema:")
        for name in tables["table_name"]:
            count = conn.execute(
                text(f"SELECT COUNT(*) FROM {quote_ident(name)}")
            ).scalar_one()
            print(f"  - {name:24s} {count:>12,} rows")

        total = conn.execute(text("SELECT COUNT(*) FROM hr_attrition")).scalar_one()
        print("\n1) Row count")
        print(f"   expected : {EXPECTED_ROWS:,}")
        print(f"   actual   : {total:,}")
        if total != EXPECTED_ROWS:
            print(f"   MISMATCH : difference {total - EXPECTED_ROWS:+,}")
            ok = False
        else:
            print("   status   : OK")

        print("\n2) DESCRIBE hr_attrition")
        describe = pd.read_sql(text("DESCRIBE hr_attrition"), conn)
        print(describe.to_string(index=False))

        print("\n3) Five sample rows")
        sample = pd.read_sql(text("SELECT * FROM hr_attrition LIMIT 5"), conn)
        print(sample.to_string(index=False))

        print("\n4) Key/index check")
        pk = pd.read_sql(
            text(
                "SELECT constraint_name, column_name "
                "FROM information_schema.key_column_usage "
                "WHERE table_schema = DATABASE() AND table_name = 'hr_attrition' "
                "AND constraint_name = 'PRIMARY' ORDER BY ordinal_position"
            ),
            conn,
        ).rename(columns=str.lower)
        indexes = pd.read_sql(
            text(
                "SELECT index_name, non_unique, seq_in_index, column_name "
                "FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND table_name = 'hr_attrition' "
                "ORDER BY index_name, seq_in_index"
            ),
            conn,
        ).rename(columns=str.lower)
        if pk.empty:
            print("   PRIMARY KEY : MISSING")
        else:
            print("   PRIMARY KEY : " + ", ".join(pk["column_name"]))
        if indexes.empty:
            print("   indexes     : none")
        else:
            print("   indexes     :")
            print(indexes.to_string(index=False))

        print("\n5) Leftover CSV index column")
        columns = pd.read_sql(
            text(
                "SELECT column_name, column_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = 'hr_attrition' "
                "ORDER BY ordinal_position"
            ),
            conn,
        ).rename(columns=str.lower)
        leftover = next(
            (
                row.column_name
                for row in columns.itertuples(index=False)
                if row.column_name.lower() in LEFT_OVER_NAMES
            ),
            None,
        )

        if leftover is None:
            print("   No 'Unnamed: 0' style column found.")
            if pk.empty:
                proposal = (
                    "ALTER TABLE hr_attrition\n"
                    "  ADD COLUMN row_id INT UNSIGNED NOT NULL AUTO_INCREMENT FIRST,\n"
                    "  ADD PRIMARY KEY (row_id);"
                )
                print("\n   Proposed DDL (NOT executed):")
                print("   " + proposal.replace("\n", "\n   "))
            else:
                print("   hr_attrition already has a primary key.")
        else:
            print(f"   Found column: {leftover!r}")
            col = quote_ident(leftover)
            _stats = conn.execute(
                text(
                    f"SELECT COUNT(*) AS total, "
                    f"COUNT({col}) AS non_null, "
                    f"COUNT(DISTINCT {col}) AS distinct_values, "
                    f"MIN({col}) AS min_value, MAX({col}) AS max_value "
                    f"FROM hr_attrition"
                )
            ).mappings().one()
            stats = {str(k).lower(): v for k, v in _stats.items()}
            print(f"   total={stats['total']:,}  non_null={stats['non_null']:,}  "
                  f"distinct={stats['distinct_values']:,}  "
                  f"min={stats['min_value']}  max={stats['max_value']}")

            unique_non_null = (
                stats["non_null"] == stats["total"]
                and stats["distinct_values"] == stats["total"]
            )
            if unique_non_null:
                print("   verdict: unique and non-null -> safe to rename to row_id and use as PK")
                if pk.empty:
                    proposal = (
                        "ALTER TABLE hr_attrition\n"
                        f"  CHANGE COLUMN {col} `row_id` INT UNSIGNED NOT NULL,\n"
                        "  ADD PRIMARY KEY (`row_id`),\n"
                        "  ADD UNIQUE KEY `uq_hr_attrition_employee_id` (`employee_id`);"
                    )
                    print("\n   Proposed DDL (NOT executed):")
                    print("   " + proposal.replace("\n", "\n   "))
                else:
                    print("   hr_attrition already has a primary key; no change needed.")
            else:
                print("   verdict: NOT unique/non-null -> cannot be used as PK.")
                print("   Proposed DDL (NOT executed): drop the column and add an AUTO_INCREMENT PK.")
                ok = False

    print("\n" + "=" * 78)
    print("Task 1 finished:", "OK" if ok else "MISMATCH/WARNING")
    print("=" * 78)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
