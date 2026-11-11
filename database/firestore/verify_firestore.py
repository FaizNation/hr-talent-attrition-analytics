"""Verify live Cloud Firestore HR summary serving layer documents and query responses.

Asserts:
1. hr_overview_summary holds 1 global document with 2,000,000 total headcount.
2. department_summary holds 7 documents with exact 2,000,000 sum headcount.
3. job_title_summary holds 29 documents.
4. work_mode_summary holds 2 documents (on_site, remote) summing to 2,000,000.
5. employee_sample holds 500 denormalized documents with 0 PII (no full_name).
6. Legacy non-HR collections are verified completely purged (0 docs).

Exits 0 on PASS, 1 on FAIL.
"""
from __future__ import annotations

import sys
from typing import Any

from config import get_firestore_client

EXPECTED_COUNTS = {
    "hr_overview_summary": 1,
    "department_summary": 7,
    "job_title_summary": 29,
    "work_mode_summary": 2,
    "employee_sample": 500,
}

REQUIRED_FIELDS = {
    "hr_overview_summary": [
        "total_employees",
        "total_payroll_inr",
        "avg_salary_inr",
        "status_distribution",
        "work_mode_distribution",
    ],
    "department_summary": [
        "department",
        "employee_count",
        "headcount_percentage",
        "total_payroll_inr",
        "avg_salary_inr",
    ],
    "job_title_summary": [
        "job_title",
        "department",
        "employee_count",
        "avg_salary_inr",
    ],
    "work_mode_summary": [
        "work_mode",
        "employee_count",
        "share_percentage",
        "avg_salary_inr",
    ],
    "employee_sample": [
        "employee_id",
        "department",
        "job_title",
        "salary_inr",
        "hire_date",
        "location",
    ],
}

PURGED_COLLECTIONS = [
    "startup_stage_presets",
    "department_benchmarks",
    "role_benchmarks",
    "work_mode_profiles",
]


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
    pii_leak_count = 0

    for doc in docs:
        d = doc.to_dict()
        data_list.append(d)
        for f in fields:
            if f not in d:
                print(f"  FAIL: doc {doc.id} missing required field '{f}'")
                missing_fields_count += 1
                ok = False
        if col_name == "employee_sample" and "full_name" in d:
            print(f"  FAIL: privacy violation: full_name found in doc {doc.id}")
            pii_leak_count += 1
            ok = False

    if missing_fields_count == 0:
        print(f"  required fields: all {len(fields)} fields present across all documents")
    if col_name == "employee_sample" and pii_leak_count == 0:
        print("  privacy check  : PASS (zero full_name attributes found in 500 records)")

    return ok, data_list


def verify_all() -> bool:
    db = get_firestore_client()
    print("=" * 65)
    print(f"Verifying Pure HR Cloud Firestore Serving Layer ({db.project})")
    print("=" * 65)

    all_ok = True
    results = {}

    # 1. Verify Active HR Collections
    for col in EXPECTED_COUNTS:
        ok, docs = verify_collection(db, col)
        results[col] = docs
        if not ok:
            all_ok = False

    # 2. Verify Purged Legacy Collections
    print("\nVerifying legacy collections purge:")
    for col in PURGED_COLLECTIONS:
        count = len(list(db.collection(col).stream()))
        status = "PASS" if count == 0 else "FAIL"
        if count != 0:
            all_ok = False
        print(f"  - legacy collection '{col}': {count} docs [{status}]")

    # 3. Specific Business Invariants
    print("\nBusiness logic invariants:")
    overview_doc = results["hr_overview_summary"][0] if results["hr_overview_summary"] else {}
    overview_hc = overview_doc.get("total_employees", 0)
    print(f"  - Global Overview headcount : {overview_hc:,} (expected 2,000,000)")
    if overview_hc != 2_000_000:
        print("    FAIL: global overview headcount != 2,000,000")
        all_ok = False
    else:
        print("    PASS")

    dept_hc = sum(int(d.get("employee_count", 0)) for d in results["department_summary"])
    print(f"  - Sum of Department headcounts: {dept_hc:,} (expected 2,000,000)")
    if dept_hc != 2_000_000:
        print("    FAIL: sum of department headcounts != 2,000,000")
        all_ok = False
    else:
        print("    PASS")

    wm_hc = sum(int(d.get("employee_count", 0)) for d in results["work_mode_summary"])
    print(f"  - Sum of Work Mode headcounts  : {wm_hc:,} (expected 2,000,000)")
    if wm_hc != 2_000_000:
        print("    FAIL: sum of work mode headcounts != 2,000,000")
        all_ok = False
    else:
        print("    PASS")

    # 4. O(1) Sample Read Test
    it_doc = db.collection("department_summary").document("IT").get()
    if it_doc.exists:
        it_data = it_doc.to_dict()
        print(
            f"\nO(1) Live Query Test: IT department has {it_data.get('employee_count'):,} employees, "
            f"avg salary = INR {it_data.get('avg_salary_inr'):,.2f}"
        )
    else:
        print("\nFAIL: O(1) read test failed: document 'IT' not found")
        all_ok = False

    print("\n" + "=" * 65)
    print(f"FINAL RESULT: {'PASS' if all_ok else 'FAIL'}")
    print("=" * 65)
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
