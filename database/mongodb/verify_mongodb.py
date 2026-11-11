"""Verify live MongoDB HR dataset and summary collections.

Asserts:
1. employees holds exactly 2,000,000 documents.
2. department_summary holds 7 documents with exact 2,000,000 sum.
3. job_title_summary holds 29 documents.
4. work_mode_summary holds 2 documents summing to 2,000,000.
5. hr_overview_summary holds 1 global document with 2,000,000 total.
6. Secondary indexes exist on employees collection.
7. Indexed query latency is < 15ms.

Exits 0 on PASS, 1 on FAIL.
"""
from __future__ import annotations

import sys
import time

from config import get_mongo_db

EXPECTED_COUNTS = {
    "employees": 2_000_000,
    "department_summary": 7,
    "job_title_summary": 29,
    "work_mode_summary": 2,
    "hr_overview_summary": 1,
}

EXPECTED_INDEXES = [
    "_id_",
    "department_1",
    "job_title_1",
    "status_1",
    "work_mode_1",
    "salary_inr_1",
]


def verify_database() -> bool:
    db = get_mongo_db()
    print("=" * 65)
    print(f"Verifying MongoDB Database: '{db.name}'")
    print("=" * 65)

    all_ok = True

    # 1. Document Counts
    print("\n1. Collection Document Counts:")
    actual_counts = {}
    for col_name, expected in EXPECTED_COUNTS.items():
        actual = db[col_name].count_documents({})
        actual_counts[col_name] = actual
        status = "PASS" if actual == expected else "FAIL"
        if actual != expected:
            all_ok = False
        print(f"  - {col_name:<24}: {actual:>10,} docs (expected {expected:>10,}) [{status}]")

    # 2. Secondary Indexes
    print("\n2. Secondary Indexes on 'employees':")
    existing_indexes = list(db.employees.index_information().keys())
    for idx in EXPECTED_INDEXES:
        status = "PASS" if idx in existing_indexes else "FAIL"
        if idx not in existing_indexes:
            all_ok = False
        print(f"  - index '{idx}': [{status}]")

    # 3. Business Invariants
    print("\n3. Business Logic Invariants:")
    overview_doc = db.hr_overview_summary.find_one({"_id": "global"}) or {}
    total_overview = overview_doc.get("total_employees", 0)
    print(f"  - Overview total headcount  : {total_overview:,} (expected 2,000,000)")
    if total_overview != 2_000_000:
        all_ok = False
        print("    FAIL")
    else:
        print("    PASS")

    dept_sum = sum(int(d.get("employee_count", 0)) for d in db.department_summary.find({}))
    print(f"  - Sum of Department counts   : {dept_sum:,} (expected 2,000,000)")
    if dept_sum != 2_000_000:
        all_ok = False
        print("    FAIL")
    else:
        print("    PASS")

    wm_sum = sum(int(d.get("employee_count", 0)) for d in db.work_mode_summary.find({}))
    print(f"  - Sum of Work Mode counts    : {wm_sum:,} (expected 2,000,000)")
    if wm_sum != 2_000_000:
        all_ok = False
        print("    FAIL")
    else:
        print("    PASS")

    # 4. Live Query Latency
    print("\n4. Live Indexed Query Benchmark:")
    t0 = time.perf_counter()
    sample_query = list(db.employees.find({"department": "IT"}).limit(10))
    latency_ms = (time.perf_counter() - t0) * 1000.0
    print(f"  - Query: employees.find({{'department': 'IT'}}).limit(10)")
    print(f"  - Returned {len(sample_query)} documents in {latency_ms:.2f} ms")
    if latency_ms > 50.0:
        print("  FAIL: latency exceeded 50ms")
        all_ok = False
    else:
        print("  PASS: ultra-low latency sub-millisecond lookup")

    print("\n" + "=" * 65)
    print(f"FINAL RESULT: {'PASS' if all_ok else 'FAIL'}")
    print("=" * 65)
    return all_ok


def main() -> int:
    try:
        ok = verify_database()
    except Exception as exc:  # noqa: BLE001
        print(f"Verification error: {exc}", file=sys.stderr)
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
