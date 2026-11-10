"""Verify live Cloud Firestore serving layer documents and query responses.

Asserts:
1. department_benchmarks holds 7 documents with required cost metrics and 2M total headcount.
2. role_benchmarks holds 29 documents with market medians and bounds.
3. work_mode_profiles holds 2 documents with overhead factors.
4. startup_stage_presets holds 3 documents with baseline burn parameters.

Exits 0 on PASS, 1 on FAIL.
"""
from __future__ import annotations

import sys
from typing import Any

from config import get_firestore_client

EXPECTED_COUNTS = {
    "department_benchmarks": 7,
    "role_benchmarks": 29,
    "work_mode_profiles": 2,
    "startup_stage_presets": 3,
}

REQUIRED_FIELDS = {
    "department_benchmarks": [
        "department",
        "employee_count",
        "headcount_percentage",
        "avg_salary_inr",
        "cost_category",
    ],
    "role_benchmarks": [
        "job_title",
        "department",
        "employee_count",
        "market_median_salary_inr",
        "min_salary_inr",
        "max_salary_inr",
    ],
    "work_mode_profiles": [
        "work_mode",
        "employee_count",
        "share_percentage",
        "overhead_factor",
    ],
    "startup_stage_presets": [
        "stage",
        "initial_cash_balance_inr",
        "monthly_revenue_inr",
        "rd_spend_ratio",
    ],
}


def verify_collection(db, col_name: str) -> tuple[bool, list[dict[str, Any]]]:
    docs = list(db.collection(col_name).stream())
    expected_count = EXPECTED_COUNTS[col_name]
    actual_count = len(docs)
    fields = REQUIRED_FIELDS[col_name]

    ok = True
    print(f"\nChecking collection: {col_name}")
    print(f"  document count : {actual_count} (expected {expected_count})")
    if actual_count != expected_count:
        print(f"  FAIL: count mismatch ({actual_count} != {expected_count})")
        ok = False

    data_list = []
    missing_fields_count = 0
    for doc in docs:
        d = doc.to_dict()
        data_list.append(d)
        for f in fields:
            if f not in d:
                print(f"  FAIL: doc {doc.id} missing required field '{f}'")
                missing_fields_count += 1
                ok = False

    if missing_fields_count == 0:
        print(f"  required fields: all {len(fields)} fields present across all documents")
    return ok, data_list


def verify_all() -> bool:
    db = get_firestore_client()
    print("=" * 60)
    print(f"Verifying Cloud Firestore serving layer (Project: {db.project})")
    print("=" * 60)

    all_ok = True
    results = {}
    for col in EXPECTED_COUNTS:
        ok, docs = verify_collection(db, col)
        results[col] = docs
        if not ok:
            all_ok = False

    # Specific business invariants
    print("\nBusiness logic invariants:")
    dept_headcount = sum(int(d.get("employee_count", 0)) for d in results["department_benchmarks"])
    print(f"  - Total department headcount: {dept_headcount:,} (expected 2,000,000)")
    if dept_headcount != 2_000_000:
        print("    FAIL: total department headcount != 2,000,000")
        all_ok = False
    else:
        print("    PASS")

    # Sample query verification (e.g. query IT department O(1))
    it_doc = db.collection("department_benchmarks").document("IT").get()
    if it_doc.exists:
        it_data = it_doc.to_dict()
        print(
            f"  - O(1) Read Test: IT avg salary = INR {it_data.get('avg_salary_inr'):,.2f}, cost = {it_data.get('cost_category')}"
        )
    else:
        print("  FAIL: Document 'IT' missing in department_benchmarks")
        all_ok = False

    print("\n" + "=" * 60)
    print(f"FINAL RESULT: {'PASS' if all_ok else 'FAIL'}")
    print("=" * 60)
    return all_ok


def main() -> int:
    try:
        ok = verify_all()
    except Exception as exc:  # noqa: BLE001
        print(f"Verification error: {exc}", file=sys.stderr)
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
