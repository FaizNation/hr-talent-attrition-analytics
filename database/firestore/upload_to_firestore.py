"""Upload aggregated HR summaries and sample records to Cloud Firestore.

Features:
1. Purges legacy non-HR collections (e.g. startup_stage_presets, old benchmarks).
2. Performs chunked atomic batch writes (< 500 operations per batch) across 5 collections:
   - hr_overview_summary (1 doc)
   - department_summary (7 docs)
   - job_title_summary (29 docs)
   - work_mode_summary (2 docs)
   - employee_sample (500 docs)
"""
from __future__ import annotations

import sys
import time
from typing import Any

from config import get_firestore_client, get_mysql_engine
from extract_from_mysql import extract_all

LEGACY_COLLECTIONS_TO_PURGE = [
    "startup_stage_presets",
    "department_benchmarks",
    "role_benchmarks",
    "work_mode_profiles",
]

BATCH_CHUNK_SIZE = 400


def purge_legacy_collections(db) -> None:
    """Delete documents in legacy collections from earlier iterations."""
    for col_name in LEGACY_COLLECTIONS_TO_PURGE:
        col_ref = db.collection(col_name)
        docs = list(col_ref.stream())
        if docs:
            print(f"Purging legacy collection '{col_name}' ({len(docs)} docs)...")
            batch = db.batch()
            for doc in docs:
                batch.delete(doc.reference)
            batch.commit()
            print(f"  purged '{col_name}' successfully.")


def upload_all(db, data: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    """Write all 539 documents into Firestore using chunked batch writes."""
    collection_map = {
        "hr_overview_summary": data["overview"],
        "department_summary": data["departments"],
        "job_title_summary": data["job_titles"],
        "work_mode_summary": data["work_modes"],
        "employee_sample": data["employee_sample"],
    }

    # Prepare flat list of (doc_ref, doc_data) operations
    operations = []
    counts = {}
    for col_name, docs in collection_map.items():
        col_ref = db.collection(col_name)
        for d in docs:
            doc_data = dict(d)
            doc_id = doc_data.pop("doc_id", None)
            if not doc_id:
                raise ValueError(f"Missing doc_id for document in {col_name}")
            doc_ref = col_ref.document(str(doc_id))
            operations.append((doc_ref, doc_data))
        counts[col_name] = len(docs)

    total_ops = len(operations)
    print(f"Submitting {total_ops} documents in chunks of {BATCH_CHUNK_SIZE}...")

    # Commit operations in batches of BATCH_CHUNK_SIZE
    for start in range(0, total_ops, BATCH_CHUNK_SIZE):
        end = min(start + BATCH_CHUNK_SIZE, total_ops)
        batch = db.batch()
        for doc_ref, doc_data in operations[start:end]:
            batch.set(doc_ref, doc_data)
        batch.commit()
        print(f"  committed batch {start + 1} to {end} / {total_ops}")

    print("All batch commits successful!")
    return counts


def main() -> int:
    t0 = time.time()
    try:
        db = get_firestore_client()
        engine = get_mysql_engine()
    except Exception as exc:  # noqa: BLE001
        print(f"Initialization error: {exc}", file=sys.stderr)
        return 1

    print(f"Target Firestore Project: {db.project}")
    purge_legacy_collections(db)

    print("Step 1: Extracting HR metrics from MySQL master...")
    data = extract_all(engine)

    print("Step 2: Uploading pure HR collections to Cloud Firestore...")
    counts = upload_all(db, data)
    for col, count in counts.items():
        print(f"  - {col:<26}: {count} documents")

    print(f"\nAll HR collections uploaded successfully in {time.time()-t0:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
