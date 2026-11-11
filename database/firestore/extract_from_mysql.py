"""Extract aggregated HR summaries and sample records from MySQL.

Generates clean, JSON-serializable payloads for the Firestore serving layer:
1. hr_overview_summary (1 macro document)
2. department_summary (7 departments)
3. job_title_summary (29 job titles)
4. work_mode_summary (2 work modes)
5. employee_sample (500 denormalized employee documents, excluding PII)
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from config import get_mysql_engine


def slugify(value: str) -> str:
    """Produce clean, URL-safe alphanumeric document IDs."""
    s = re.sub(r"[^0-9a-zA-Z]+", "_", value.strip()).strip("_").lower()
    return s or "item"


def extract_overview(engine: Engine) -> list[dict[str, Any]]:
    print("  extracting global overview...")
    stats_sql = """
        SELECT
            COUNT(*) AS total_employees,
            SUM(salary_inr) AS total_payroll_inr,
            ROUND(AVG(salary_inr), 2) AS avg_salary_inr,
            MIN(salary_inr) AS min_salary_inr,
            MAX(salary_inr) AS max_salary_inr,
            ROUND(AVG(experience_years), 2) AS avg_experience_years,
            ROUND(AVG(performance_rating), 2) AS avg_performance_rating
        FROM hr_employee
    """
    status_sql = "SELECT status, COUNT(*) AS cnt FROM hr_employee GROUP BY status"
    work_mode_sql = "SELECT work_mode, COUNT(*) AS cnt FROM hr_employee GROUP BY work_mode"

    with engine.connect() as conn:
        stats = conn.execute(text(stats_sql)).mappings().one()
        status_rows = conn.execute(text(status_sql)).mappings().all()
        wm_rows = conn.execute(text(work_mode_sql)).mappings().all()

    now_iso = datetime.now(timezone.utc).isoformat()
    return [{
        "doc_id": "global",
        "total_employees": int(stats["total_employees"]),
        "total_payroll_inr": int(stats["total_payroll_inr"] or 0),
        "avg_salary_inr": float(stats["avg_salary_inr"] or 0.0),
        "min_salary_inr": int(stats["min_salary_inr"] or 0),
        "max_salary_inr": int(stats["max_salary_inr"] or 0),
        "avg_experience_years": float(stats["avg_experience_years"] or 0.0),
        "avg_performance_rating": float(stats["avg_performance_rating"] or 0.0),
        "status_distribution": {str(r["status"]): int(r["cnt"]) for r in status_rows},
        "work_mode_distribution": {str(r["work_mode"]): int(r["cnt"]) for r in wm_rows},
        "updated_at": now_iso,
    }]


def extract_departments(engine: Engine) -> list[dict[str, Any]]:
    print("  extracting department summaries...")
    sql = """
        SELECT
            d.department,
            COUNT(e.row_id) AS employee_count,
            SUM(e.salary_inr) AS total_payroll_inr,
            ROUND(AVG(e.salary_inr), 2) AS avg_salary_inr,
            MIN(e.salary_inr) AS min_salary_inr,
            MAX(e.salary_inr) AS max_salary_inr,
            ROUND(AVG(e.experience_years), 2) AS avg_experience_years,
            ROUND(AVG(e.performance_rating), 2) AS avg_performance_rating
        FROM dim_department d
        LEFT JOIN hr_employee e ON d.department = e.department
        GROUP BY d.department
        ORDER BY d.department
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).mappings().all()

    total_employees = sum(int(r["employee_count"]) for r in rows)
    now_iso = datetime.now(timezone.utc).isoformat()
    out = []
    for r in rows:
        cnt = int(r["employee_count"])
        pct = round(100.0 * cnt / total_employees, 2) if total_employees else 0.0
        dept = str(r["department"])
        out.append({
            "doc_id": dept,
            "department": dept,
            "employee_count": cnt,
            "headcount_percentage": pct,
            "total_payroll_inr": int(r["total_payroll_inr"] or 0),
            "avg_salary_inr": float(r["avg_salary_inr"] or 0.0),
            "min_salary_inr": int(r["min_salary_inr"] or 0),
            "max_salary_inr": int(r["max_salary_inr"] or 0),
            "avg_experience_years": float(r["avg_experience_years"] or 0.0),
            "avg_performance_rating": float(r["avg_performance_rating"] or 0.0),
            "updated_at": now_iso,
        })
    return out


def extract_job_titles(engine: Engine) -> list[dict[str, Any]]:
    print("  extracting job title summaries...")
    sql = """
        SELECT
            j.job_title,
            e.department,
            COUNT(e.row_id) AS employee_count,
            MIN(e.salary_inr) AS min_salary_inr,
            MAX(e.salary_inr) AS max_salary_inr,
            ROUND(AVG(e.salary_inr), 2) AS avg_salary_inr,
            ROUND(AVG(e.experience_years), 2) AS avg_experience_years,
            ROUND(AVG(e.performance_rating), 2) AS avg_performance_rating
        FROM dim_job_title j
        LEFT JOIN hr_employee e ON j.job_title = e.job_title
        GROUP BY j.job_title, e.department
        ORDER BY j.job_title
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).mappings().all()

    now_iso = datetime.now(timezone.utc).isoformat()
    out = []
    for r in rows:
        title = str(r["job_title"])
        dept = str(r["department"])
        out.append({
            "doc_id": slugify(title),
            "job_title": title,
            "department": dept,
            "employee_count": int(r["employee_count"]),
            "avg_salary_inr": float(r["avg_salary_inr"] or 0.0),
            "min_salary_inr": int(r["min_salary_inr"] or 0),
            "max_salary_inr": int(r["max_salary_inr"] or 0),
            "avg_experience_years": float(r["avg_experience_years"] or 0.0),
            "avg_performance_rating": float(r["avg_performance_rating"] or 0.0),
            "updated_at": now_iso,
        })
    return out


def extract_work_modes(engine: Engine) -> list[dict[str, Any]]:
    print("  extracting work mode summaries...")
    sql = """
        SELECT
            w.work_mode,
            COUNT(e.row_id) AS employee_count,
            ROUND(AVG(e.salary_inr), 2) AS avg_salary_inr,
            ROUND(AVG(e.performance_rating), 2) AS avg_performance_rating
        FROM dim_work_mode w
        LEFT JOIN hr_employee e ON w.work_mode = e.work_mode
        GROUP BY w.work_mode
        ORDER BY w.work_mode
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).mappings().all()

    total_employees = sum(int(r["employee_count"]) for r in rows)
    now_iso = datetime.now(timezone.utc).isoformat()
    out = []
    for r in rows:
        mode = str(r["work_mode"])
        cnt = int(r["employee_count"])
        pct = round(100.0 * cnt / total_employees, 2) if total_employees else 0.0
        out.append({
            "doc_id": slugify(mode),
            "work_mode": mode,
            "employee_count": cnt,
            "share_percentage": pct,
            "avg_salary_inr": float(r["avg_salary_inr"] or 0.0),
            "avg_performance_rating": float(r["avg_performance_rating"] or 0.0),
            "updated_at": now_iso,
        })
    return out


def extract_employee_sample(engine: Engine, limit: int = 500) -> list[dict[str, Any]]:
    print(f"  extracting {limit} sample employee records (omitting full_name for privacy)...")
    sql = """
        SELECT
            employee_id,
            department,
            job_title,
            hire_date,
            location,
            performance_rating,
            experience_years,
            status,
            work_mode,
            salary_inr
        FROM hr_employee
        ORDER BY row_id
        LIMIT :limit
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"limit": limit}).mappings().all()

    now_iso = datetime.now(timezone.utc).isoformat()
    out = []
    for r in rows:
        emp_id = str(r["employee_id"])
        out.append({
            "doc_id": emp_id,
            "employee_id": emp_id,
            "department": str(r["department"]),
            "job_title": str(r["job_title"]),
            "hire_date": str(r["hire_date"]),
            "location": str(r["location"]),
            "performance_rating": int(r["performance_rating"]),
            "experience_years": int(r["experience_years"]),
            "status": str(r["status"]),
            "work_mode": str(r["work_mode"]),
            "salary_inr": int(r["salary_inr"]),
            "extracted_at": now_iso,
        })
    return out


def extract_all(engine: Engine) -> dict[str, list[dict[str, Any]]]:
    return {
        "overview": extract_overview(engine),
        "departments": extract_departments(engine),
        "job_titles": extract_job_titles(engine),
        "work_modes": extract_work_modes(engine),
        "employee_sample": extract_employee_sample(engine, limit=500),
    }


def main() -> int:
    engine = get_mysql_engine()
    print("Extracting pure HR summaries & sample records from MySQL master...")
    data = extract_all(engine)

    overview_count = len(data["overview"])
    dept_count = len(data["departments"])
    title_count = len(data["job_titles"])
    mode_count = len(data["work_modes"])
    sample_count = len(data["employee_sample"])
    total_dept_headcount = sum(d["employee_count"] for d in data["departments"])

    print(f"  overview        : {overview_count} doc (total headcount: {data['overview'][0]['total_employees']:,})")
    print(f"  departments     : {dept_count} docs (sum: {total_dept_headcount:,})")
    print(f"  job_titles      : {title_count} docs")
    print(f"  work_modes      : {mode_count} docs")
    print(f"  employee_sample : {sample_count} docs")

    if (
        overview_count != 1
        or dept_count != 7
        or title_count != 29
        or mode_count != 2
        or sample_count != 500
    ):
        print("FAIL: unexpected document counts in extracted collections")
        return 1

    if total_dept_headcount != 2_000_000:
        print(f"FAIL: total department headcount {total_dept_headcount:,} != 2,000,000")
        return 1

    print("MySQL HR extraction: PASS")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
