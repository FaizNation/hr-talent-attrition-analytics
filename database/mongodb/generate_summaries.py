"""Generate analytical summary collections in MongoDB using native Aggregation Pipelines.

Consumes:
- db_hr_mnc.employees (2,000,000 documents)

Produces:
- hr_overview_summary (1 document: _id = "global")
- department_summary (7 documents)
- job_title_summary (29 documents)
- work_mode_summary (2 documents)
"""
from __future__ import annotations

import re
import sys
import time
from datetime import datetime, timezone
from typing import Any

from config import get_mongo_db

EXPECTED_EMPLOYEES = 2_000_000


def slugify(value: str) -> str:
    """Produce clean, alphanumeric document IDs."""
    s = re.sub(r"[^0-9a-zA-Z]+", "_", value.strip()).strip("_").lower()
    return s or "item"


def generate_overview(db: Any) -> dict[str, Any]:
    print("  running native aggregation for hr_overview_summary...")
    t0 = time.time()
    pipeline = [
        {
            "$facet": {
                "stats": [
                    {
                        "$group": {
                            "_id": None,
                            "total_employees": {"$sum": 1},
                            "total_payroll_inr": {"$sum": "$salary_inr"},
                            "avg_salary_inr": {"$avg": "$salary_inr"},
                            "min_salary_inr": {"$min": "$salary_inr"},
                            "max_salary_inr": {"$max": "$salary_inr"},
                            "avg_experience_years": {"$avg": "$experience_years"},
                            "avg_performance_rating": {"$avg": "$performance_rating"},
                        }
                    }
                ],
                "status": [
                    {"$group": {"_id": "$status", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                ],
                "work_mode": [
                    {"$group": {"_id": "$work_mode", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                ],
            }
        }
    ]

    res = list(db.employees.aggregate(pipeline))[0]
    stats = res["stats"][0] if res["stats"] else {}
    status_dist = {str(item["_id"]): int(item["count"]) for item in res["status"]}
    wm_dist = {str(item["_id"]): int(item["count"]) for item in res["work_mode"]}

    now_iso = datetime.now(timezone.utc).isoformat()
    overview_doc = {
        "_id": "global",
        "total_employees": int(stats.get("total_employees", 0)),
        "total_payroll_inr": int(stats.get("total_payroll_inr", 0)),
        "avg_salary_inr": round(float(stats.get("avg_salary_inr", 0.0)), 2),
        "min_salary_inr": int(stats.get("min_salary_inr", 0)),
        "max_salary_inr": int(stats.get("max_salary_inr", 0)),
        "avg_experience_years": round(float(stats.get("avg_experience_years", 0.0)), 2),
        "avg_performance_rating": round(float(stats.get("avg_performance_rating", 0.0)), 2),
        "status_distribution": status_dist,
        "work_mode_distribution": wm_dist,
        "generated_at": now_iso,
    }

    db.hr_overview_summary.replace_one({"_id": "global"}, overview_doc, upsert=True)
    print(f"  overview generated in {time.time()-t0:.2f}s (headcount: {overview_doc['total_employees']:,})")
    return overview_doc


def generate_departments(db: Any, total_employees: int) -> int:
    print("  running native aggregation for department_summary...")
    t0 = time.time()
    pipeline = [
        {
            "$group": {
                "_id": "$department",
                "department": {"$first": "$department"},
                "employee_count": {"$sum": 1},
                "total_payroll_inr": {"$sum": "$salary_inr"},
                "avg_salary_inr": {"$avg": "$salary_inr"},
                "min_salary_inr": {"$min": "$salary_inr"},
                "max_salary_inr": {"$max": "$salary_inr"},
                "avg_experience_years": {"$avg": "$experience_years"},
                "avg_performance_rating": {"$avg": "$performance_rating"},
            }
        },
        {"$sort": {"department": 1}},
    ]

    dept_rows = list(db.employees.aggregate(pipeline))
    now_iso = datetime.now(timezone.utc).isoformat()

    for r in dept_rows:
        cnt = int(r["employee_count"])
        pct = round(100.0 * cnt / total_employees, 2) if total_employees else 0.0
        doc = {
            "_id": str(r["department"]),
            "department": str(r["department"]),
            "employee_count": cnt,
            "headcount_percentage": pct,
            "total_payroll_inr": int(r["total_payroll_inr"]),
            "avg_salary_inr": round(float(r["avg_salary_inr"]), 2),
            "min_salary_inr": int(r["min_salary_inr"]),
            "max_salary_inr": int(r["max_salary_inr"]),
            "avg_experience_years": round(float(r["avg_experience_years"]), 2),
            "avg_performance_rating": round(float(r["avg_performance_rating"]), 2),
            "generated_at": now_iso,
        }
        db.department_summary.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    print(f"  {len(dept_rows)} departments generated in {time.time()-t0:.2f}s")
    return len(dept_rows)


def generate_job_titles(db: Any) -> int:
    print("  running native aggregation for job_title_summary...")
    t0 = time.time()
    pipeline = [
        {
            "$group": {
                "_id": "$job_title",
                "job_title": {"$first": "$job_title"},
                "department": {"$first": "$department"},
                "employee_count": {"$sum": 1},
                "avg_salary_inr": {"$avg": "$salary_inr"},
                "min_salary_inr": {"$min": "$salary_inr"},
                "max_salary_inr": {"$max": "$salary_inr"},
                "avg_experience_years": {"$avg": "$experience_years"},
                "avg_performance_rating": {"$avg": "$performance_rating"},
            }
        },
        {"$sort": {"job_title": 1}},
    ]

    job_rows = list(db.employees.aggregate(pipeline))
    now_iso = datetime.now(timezone.utc).isoformat()

    for r in job_rows:
        title = str(r["job_title"])
        doc = {
            "_id": slugify(title),
            "job_title": title,
            "department": str(r["department"]),
            "employee_count": int(r["employee_count"]),
            "avg_salary_inr": round(float(r["avg_salary_inr"]), 2),
            "min_salary_inr": int(r["min_salary_inr"]),
            "max_salary_inr": int(r["max_salary_inr"]),
            "avg_experience_years": round(float(r["avg_experience_years"]), 2),
            "avg_performance_rating": round(float(r["avg_performance_rating"]), 2),
            "generated_at": now_iso,
        }
        db.job_title_summary.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    print(f"  {len(job_rows)} job titles generated in {time.time()-t0:.2f}s")
    return len(job_rows)


def generate_work_modes(db: Any, total_employees: int) -> int:
    print("  running native aggregation for work_mode_summary...")
    t0 = time.time()
    pipeline = [
        {
            "$group": {
                "_id": "$work_mode",
                "work_mode": {"$first": "$work_mode"},
                "employee_count": {"$sum": 1},
                "avg_salary_inr": {"$avg": "$salary_inr"},
                "avg_performance_rating": {"$avg": "$performance_rating"},
            }
        },
        {"$sort": {"work_mode": 1}},
    ]

    wm_rows = list(db.employees.aggregate(pipeline))
    now_iso = datetime.now(timezone.utc).isoformat()

    for r in wm_rows:
        mode = str(r["work_mode"])
        cnt = int(r["employee_count"])
        pct = round(100.0 * cnt / total_employees, 2) if total_employees else 0.0
        doc = {
            "_id": slugify(mode),
            "work_mode": mode,
            "employee_count": cnt,
            "share_percentage": pct,
            "avg_salary_inr": round(float(r["avg_salary_inr"]), 2),
            "avg_performance_rating": round(float(r["avg_performance_rating"]), 2),
            "generated_at": now_iso,
        }
        db.work_mode_summary.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    print(f"  {len(wm_rows)} work modes generated in {time.time()-t0:.2f}s")
    return len(wm_rows)


def generate_all_summaries(db: Any) -> dict[str, int]:
    t_start = time.time()
    total_docs = db.employees.count_documents({})
    if total_docs != EXPECTED_EMPLOYEES:
        raise ValueError(
            f"Collection 'employees' has {total_docs:,} documents, expected {EXPECTED_EMPLOYEES:,}."
        )

    print("Generating MongoDB summary collections from 2,000,000 employee documents...")
    overview = generate_overview(db)
    dept_count = generate_departments(db, overview["total_employees"])
    job_count = generate_job_titles(db)
    wm_count = generate_work_modes(db, overview["total_employees"])

    print(f"All aggregation pipelines completed successfully in {time.time()-t_start:.2f}s")
    return {
        "hr_overview_summary": 1,
        "department_summary": dept_count,
        "job_title_summary": job_count,
        "work_mode_summary": wm_count,
    }


def main() -> int:
    db = get_mongo_db()
    try:
        counts = generate_all_summaries(db)
        print("\nSummary collection counts:")
        for col, c in counts.items():
            print(f"  - {col:<26}: {c} documents")
    except Exception as exc:  # noqa: BLE001
        print(f"Aggregation error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
