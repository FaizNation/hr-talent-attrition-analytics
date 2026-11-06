"""Task 5: run the aggregate/join queries and write JSON results.

Outputs (database/sql/output/):
  q1_underpaid.json
  q2_talent_segments.json
  q3_branch_efficiency.json
  q4_join_branch.json
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from config import OUTPUT_DIR, get_engine

Q1 = """
SELECT
    COUNT(*) AS total_employees,
    SUM(salary_disparity_index < 0.9) AS underpaid_employees,
    ROUND(100.0 * SUM(salary_disparity_index < 0.9) / COUNT(*), 4) AS underpaid_pct
FROM hr_features
"""

Q2 = """
SELECT
    talent_segment,
    COUNT(*) AS employee_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM hr_features), 4) AS percentage
FROM hr_features
GROUP BY talent_segment
ORDER BY employee_count DESC
"""

Q3 = """
SELECT
    country,
    department,
    work_mode,
    total_employees,
    attrition_count,
    turnover_rate_pct,
    avg_salary_disparity,
    avg_performance
FROM branch_efficiency
ORDER BY country, department, work_mode
"""

Q4_SUMMARY = """
SELECT
    (SELECT COUNT(*) FROM hr_features) AS feature_rows,
    (SELECT COUNT(*) FROM branch_efficiency) AS branch_rows,
    (SELECT COUNT(*)
       FROM hr_features f
       JOIN branch_efficiency b
         ON f.country = b.country
        AND f.department = b.department
        AND f.work_mode = b.work_mode) AS joined_rows,
    (SELECT COUNT(*)
       FROM hr_features f
       LEFT JOIN branch_efficiency b
         ON f.country = b.country
        AND f.department = b.department
        AND f.work_mode = b.work_mode
       WHERE b.country IS NULL) AS feature_rows_without_branch,
    (SELECT COUNT(*)
       FROM branch_efficiency b
       LEFT JOIN hr_features f
         ON f.country = b.country
        AND f.department = b.department
        AND f.work_mode = b.work_mode
       WHERE f.employee_id IS NULL) AS branch_rows_without_features
"""

Q4_BRANCHES = """
SELECT
    b.country,
    b.department,
    b.work_mode,
    COUNT(f.employee_id) AS actual_employees,
    b.total_employees AS branch_total_employees,
    b.attrition_count,
    b.turnover_rate_pct,
    ROUND(AVG(f.salary_disparity_index), 4) AS avg_sdi,
    ROUND(AVG(f.performance_rating), 3) AS avg_performance
FROM branch_efficiency b
LEFT JOIN hr_features f
  ON f.country = b.country
 AND f.department = b.department
 AND f.work_mode = b.work_mode
GROUP BY b.country, b.department, b.work_mode,
         b.total_employees, b.attrition_count, b.turnover_rate_pct
ORDER BY b.country, b.department, b.work_mode
"""

Q4_MISMATCHES = """
SELECT COUNT(*) AS mismatched_branches
FROM (
    SELECT b.country, b.department, b.work_mode, b.total_employees,
           COUNT(f.employee_id) AS actual_employees
    FROM branch_efficiency b
    LEFT JOIN hr_features f
      ON f.country = b.country
     AND f.department = b.department
     AND f.work_mode = b.work_mode
    GROUP BY b.country, b.department, b.work_mode, b.total_employees
    HAVING COUNT(f.employee_id) <> b.total_employees
) AS mismatches
"""


def records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-safe list of dicts (Decimal/numpy handled by pandas)."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  wrote {path.name} ({path.stat().st_size:,} bytes)")


def run(engine: Engine, output_dir: Path) -> bool:
    generated_at = datetime.now(timezone.utc).isoformat()
    ok = True

    print("Task 5 - aggregate queries")
    with engine.connect() as conn:
        q1_df = pd.read_sql(text(Q1), conn).rename(columns=str.lower)
        q1 = records(q1_df)[0]
        write_json(
            output_dir / "q1_underpaid.json",
            {
                "description": "Total employees and underpaid employees (SDI < 0.9)",
                "generated_at": generated_at,
                "result": q1,
            },
        )

        q2_df = pd.read_sql(text(Q2), conn).rename(columns=str.lower)
        q2 = records(q2_df)
        write_json(
            output_dir / "q2_talent_segments.json",
            {
                "description": "Employee count and percentage per Talent_Segment",
                "generated_at": generated_at,
                "total_employees": sum(row["employee_count"] for row in q2),
                "segments": q2,
            },
        )

        q3_df = pd.read_sql(text(Q3), conn).rename(columns=str.lower)
        write_json(
            output_dir / "q3_branch_efficiency.json",
            {
                "description": "Branch efficiency data (one row per country/department/work_mode)",
                "generated_at": generated_at,
                "row_count": int(len(q3_df)),
                "data": records(q3_df),
            },
        )

        summary = records(
            pd.read_sql(text(Q4_SUMMARY), conn).rename(columns=str.lower)
        )[0]
        branches = records(
            pd.read_sql(text(Q4_BRANCHES), conn).rename(columns=str.lower)
        )
        mismatches = records(
            pd.read_sql(text(Q4_MISMATCHES), conn).rename(columns=str.lower)
        )[0]["mismatched_branches"]
        write_json(
            output_dir / "q4_join_branch.json",
            {
                "description": (
                    "JOIN proof: every hr_features row maps to exactly one "
                    "branch_efficiency row on (country, department, work_mode)"
                ),
                "generated_at": generated_at,
                "summary": summary,
                "mismatched_branches": mismatches,
                "branches": branches,
            },
        )

        print("\nSummary")
        print(f"  Q1 total/underpaid: {q1}")
        print(f"  Q2 segments       : {len(q2)}")
        print(f"  Q3 branch rows    : {len(q3_df):,}")
        print(f"  Q4 summary        : {summary}")
        print(f"  Q4 mismatches     : {mismatches}")

        if summary["feature_rows"] != summary["joined_rows"]:
            print("  FAIL: not every feature row joined to a branch")
            ok = False
        if summary["feature_rows_without_branch"] or summary["branch_rows_without_features"]:
            print("  FAIL: unmatched rows exist on one side of the JOIN")
            ok = False
        if mismatches:
            print("  FAIL: branch employee counts do not match the fact table")
            ok = False
        if len(q3_df) != 3402:
            print("  FAIL: expected 3,402 branch rows")
            ok = False

    return ok


def main() -> int:
    engine = get_engine()
    ok = run(engine, OUTPUT_DIR)
    print("\nTask 5:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
