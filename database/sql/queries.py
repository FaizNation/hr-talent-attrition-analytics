"""Reporting queries over the normalized raw HR schema.

Outputs (database/sql/output/):
  q1_headcount_by_department.json
  q2_salary_by_job_title.json
  q3_work_mode_split.json
  q4_hire_cohort.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from config import OUTPUT_DIR, get_engine

Q1_DEPARTMENT = """
SELECT
    d.department,
    COUNT(e.row_id) AS employee_count,
    ROUND(100.0 * COUNT(e.row_id) / (SELECT COUNT(*) FROM hr_employee), 4) AS percentage,
    ROUND(AVG(e.salary_inr), 2) AS avg_salary_inr
FROM dim_department d
LEFT JOIN hr_employee e ON d.department = e.department
GROUP BY d.department
ORDER BY employee_count DESC
"""

Q2_JOB_TITLE = """
SELECT
    j.job_title,
    COUNT(e.row_id) AS employee_count,
    MIN(e.salary_inr) AS min_salary_inr,
    ROUND(AVG(e.salary_inr), 2) AS avg_salary_inr,
    MAX(e.salary_inr) AS max_salary_inr
FROM dim_job_title j
LEFT JOIN hr_employee e ON j.job_title = e.job_title
GROUP BY j.job_title
ORDER BY employee_count DESC
"""

Q3_WORK_MODE = """
SELECT
    w.work_mode,
    COUNT(e.row_id) AS employee_count,
    ROUND(100.0 * COUNT(e.row_id) / (SELECT COUNT(*) FROM hr_employee), 4) AS percentage,
    ROUND(AVG(e.salary_inr), 2) AS avg_salary_inr
FROM dim_work_mode w
LEFT JOIN hr_employee e ON w.work_mode = e.work_mode
GROUP BY w.work_mode
ORDER BY employee_count DESC
"""

Q4_HIRE_COHORT = """
SELECT
    YEAR(hire_date) AS hire_year,
    COUNT(*) AS employee_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM hr_employee), 4) AS percentage,
    ROUND(AVG(salary_inr), 2) AS avg_salary_inr
FROM hr_employee
GROUP BY YEAR(hire_date)
ORDER BY hire_year ASC
"""


def records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-safe list of dicts (handles Decimal/numpy/int64)."""
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

    print("Task 4 - reporting queries over normalized schema")
    with engine.connect() as conn:
        print("  running q1 (department headcount & avg salary)...")
        q1_df = pd.read_sql(text(Q1_DEPARTMENT), conn).rename(columns=str.lower)
        q1_rows = records(q1_df)
        total_q1 = sum(row["employee_count"] for row in q1_rows)
        write_json(
            output_dir / "q1_headcount_by_department.json",
            {
                "description": "Headcount, percentage share, and average salary by department",
                "generated_at": generated_at,
                "total_employees": total_q1,
                "departments": q1_rows,
            },
        )

        print("  running q2 (job title headcount & min/avg/max salary)...")
        q2_df = pd.read_sql(text(Q2_JOB_TITLE), conn).rename(columns=str.lower)
        q2_rows = records(q2_df)
        write_json(
            output_dir / "q2_salary_by_job_title.json",
            {
                "description": "Headcount and salary bounds (min, avg, max) by job title",
                "generated_at": generated_at,
                "job_titles_count": len(q2_rows),
                "job_titles": q2_rows,
            },
        )

        print("  running q3 (work mode split & avg salary)...")
        q3_df = pd.read_sql(text(Q3_WORK_MODE), conn).rename(columns=str.lower)
        q3_rows = records(q3_df)
        write_json(
            output_dir / "q3_work_mode_split.json",
            {
                "description": "Headcount and average salary by work mode",
                "generated_at": generated_at,
                "work_modes": q3_rows,
            },
        )

        print("  running q4 (hire cohort by year)...")
        q4_df = pd.read_sql(text(Q4_HIRE_COHORT), conn).rename(columns=str.lower)
        q4_rows = records(q4_df)
        write_json(
            output_dir / "q4_hire_cohort.json",
            {
                "description": "Annual hiring cohort headcount and average salary (2010-2025)",
                "generated_at": generated_at,
                "cohorts": q4_rows,
            },
        )

        # Integrity verification: department headcount total must equal hr_employee total
        total_employee = conn.execute(text("SELECT COUNT(*) FROM hr_employee")).scalar_one()
        print(f"\nIntegrity check: department headcount total = {total_q1:,}, hr_employee rows = {total_employee:,}")
        if total_q1 != total_employee or total_employee != 2_000_000:
            print(f"  FAIL: sum of department headcounts ({total_q1:,}) != hr_employee ({total_employee:,})")
            ok = False
        else:
            print("  PASS: department headcount sum exactly matches 2,000,000 employee rows")

    print("\nRESULT:", "PASS" if ok else "FAIL")
    return ok


def main() -> int:
    engine = get_engine()
    return 0 if run(engine, OUTPUT_DIR) else 1


if __name__ == "__main__":
    sys.exit(main())
