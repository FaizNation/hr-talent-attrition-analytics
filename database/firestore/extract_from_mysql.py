"""Extract aggregated runway and workforce cost metrics from MySQL.

Generates clean, JSON-serializable payloads for the Firestore serving layer:
1. department_benchmarks (7 departments)
2. role_benchmarks (29 job titles with market medians)
3. work_mode_profiles (2 work modes with overhead factors)
4. startup_stage_presets (3 venture stages with financial baselines)
"""
from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from config import PROJECT_ROOT, get_mysql_engine

DEPT_COST_CATEGORIES = {
    "IT": "R&D / Product Spend",
    "R&D": "R&D / Product Spend",
    "Sales": "Marketing & Growth Spend",
    "Marketing": "Marketing & Growth Spend",
    "Finance": "Administration & G&A Spend",
    "HR": "Administration & G&A Spend",
    "Operations": "Administration & G&A Spend",
}

OVERHEAD_FACTORS = {
    "On-site": (1.20, "Requires office physical facility & workstation overhead (1.20x)"),
    "Remote": (1.03, "Low overhead; home office allowance & collaboration tool cost (1.03x)"),
}

STARTUP_PRESETS = [
    {
        "stage": "Seed",
        "initial_cash_balance_inr": 35_000_000.0,
        "monthly_revenue_inr": 300_000.0,
        "revenue_growth_rate": 0.060,
        "rd_spend_ratio": 0.550,
        "admin_spend_ratio": 0.150,
        "marketing_spend_ratio": 0.300,
        "non_payroll_opex_ratio": 0.250,
    },
    {
        "stage": "Series A",
        "initial_cash_balance_inr": 150_000_000.0,
        "monthly_revenue_inr": 2_500_000.0,
        "revenue_growth_rate": 0.045,
        "rd_spend_ratio": 0.450,
        "admin_spend_ratio": 0.175,
        "marketing_spend_ratio": 0.375,
        "non_payroll_opex_ratio": 0.300,
    },
    {
        "stage": "Series B",
        "initial_cash_balance_inr": 450_000_000.0,
        "monthly_revenue_inr": 9_000_000.0,
        "revenue_growth_rate": 0.030,
        "rd_spend_ratio": 0.350,
        "admin_spend_ratio": 0.200,
        "marketing_spend_ratio": 0.450,
        "non_payroll_opex_ratio": 0.350,
    },
]


def slugify(value: str) -> str:
    """Produce clean, URL-safe alphanumeric document IDs."""
    s = re.sub(r"[^0-9a-zA-Z]+", "_", value.strip()).strip("_").lower()
    return s or "item"


def load_role_medians() -> dict[str, float]:
    """Read precomputed market median salary per role from CSV if present."""
    csv_path = PROJECT_ROOT / "artifacts_runway" / "role_median_salary.csv"
    medians: dict[str, float] = {}
    if csv_path.exists():
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                title = r.get("Job_Title", "").strip()
                med = float(r.get("Median_Salary_INR", 0.0))
                if title:
                    medians[title] = med
    return medians


def extract_departments(engine: Engine) -> list[dict[str, Any]]:
    sql = """
        SELECT
            d.department,
            COUNT(e.row_id) AS employee_count,
            ROUND(AVG(e.salary_inr), 2) AS avg_salary_inr,
            MIN(e.salary_inr) AS min_salary_inr,
            MAX(e.salary_inr) AS max_salary_inr
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
            "avg_salary_inr": float(r["avg_salary_inr"] or 0.0),
            "min_salary_inr": int(r["min_salary_inr"] or 0),
            "max_salary_inr": int(r["max_salary_inr"] or 0),
            "cost_category": DEPT_COST_CATEGORIES.get(dept, "General & Administrative (G&A)"),
            "updated_at": now_iso,
        })
    return out


def extract_roles(engine: Engine) -> list[dict[str, Any]]:
    role_medians = load_role_medians()
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
        avg_sal = float(r["avg_salary_inr"] or 0.0)
        med_sal = role_medians.get(title, avg_sal)
        doc_id = slugify(title)
        out.append({
            "doc_id": doc_id,
            "job_title": title,
            "department": dept,
            "employee_count": int(r["employee_count"]),
            "market_median_salary_inr": med_sal,
            "min_salary_inr": int(r["min_salary_inr"] or 0),
            "max_salary_inr": int(r["max_salary_inr"] or 0),
            "avg_salary_inr": avg_sal,
            "avg_experience_years": float(r["avg_experience_years"] or 0.0),
            "avg_performance_rating": float(r["avg_performance_rating"] or 0.0),
            "cost_category": DEPT_COST_CATEGORIES.get(dept, "Administration & G&A Spend"),
            "updated_at": now_iso,
        })
    return out


def extract_work_modes(engine: Engine) -> list[dict[str, Any]]:
    sql = """
        SELECT
            w.work_mode,
            COUNT(e.row_id) AS employee_count,
            ROUND(AVG(e.salary_inr), 2) AS avg_salary_inr
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
        overhead, desc = OVERHEAD_FACTORS.get(mode, (1.00, "Standard overhead"))
        out.append({
            "doc_id": slugify(mode),
            "work_mode": mode,
            "employee_count": cnt,
            "share_percentage": pct,
            "avg_salary_inr": float(r["avg_salary_inr"] or 0.0),
            "overhead_factor": overhead,
            "description": desc,
            "updated_at": now_iso,
        })
    return out


def extract_presets() -> list[dict[str, Any]]:
    now_iso = datetime.now(timezone.utc).isoformat()
    out = []
    for p in STARTUP_PRESETS:
        item = dict(p)
        item["doc_id"] = slugify(item["stage"])
        item["updated_at"] = now_iso
        out.append(item)
    return out


def extract_all(engine: Engine) -> dict[str, list[dict[str, Any]]]:
    return {
        "departments": extract_departments(engine),
        "roles": extract_roles(engine),
        "work_modes": extract_work_modes(engine),
        "presets": extract_presets(),
    }


def main() -> int:
    engine = get_mysql_engine()
    print("Extracting aggregated runway metrics from MySQL master...")
    data = extract_all(engine)

    dept_count = len(data["departments"])
    role_count = len(data["roles"])
    mode_count = len(data["work_modes"])
    preset_count = len(data["presets"])
    total_dept_headcount = sum(d["employee_count"] for d in data["departments"])

    print(f"  departments : {dept_count} docs (total headcount: {total_dept_headcount:,})")
    print(f"  roles       : {role_count} docs")
    print(f"  work_modes  : {mode_count} docs")
    print(f"  presets     : {preset_count} docs")

    if dept_count != 7 or role_count != 29 or mode_count != 2 or preset_count != 3:
        print("FAIL: unexpected document counts in extracted collections")
        return 1

    if total_dept_headcount != 2_000_000:
        print(f"FAIL: total headcount {total_dept_headcount:,} != 2,000,000")
        return 1

    print("MySQL extraction: PASS")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
