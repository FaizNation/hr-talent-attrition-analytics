"""Upload aggregated runway and workforce cost metrics to Cloud Firestore.

Performs idempotent batched writes to 4 collections:
1. department_benchmarks (7 docs)
2. role_benchmarks (29 docs)
3. work_mode_profiles (2 docs)
4. startup_stage_presets (3 docs)
"""
from __future__ import annotations

import sys
import time
from typing import Any

from config import get_firestore_client, get_mysql_engine
from extract_from_mysql import extract_all


def upload_all(db, data: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    """Write all extracted documents into Firestore in an atomic batch."""
    batch = db.batch()
    counts = {}

    collection_map = {
        "department_benchmarks": data["departments"],
        "role_benchmarks": data["roles"],
        "work_mode_profiles": data["work_modes"],
        "startup_stage_presets": data["presets"],
    }

    total_ops = 0
    for col_name, docs in collection_map.items():
        col_ref = db.collection(col_name)
        for d in docs:
            doc_data = dict(d)
            doc_id = doc_data.pop("doc_id", None)
            if not doc_id:
                raise ValueError(f"Missing doc_id for document in {col_name}")
            doc_ref = col_ref.document(str(doc_id))
            batch.set(doc_ref, doc_data)
            total_ops += 1
        counts[col_name] = len(docs)

    print(f"Submitting batched write ({total_ops} documents across 4 collections)...")
    batch.commit()
    print("Batch commit successful!")
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
    print("Step 1: Extracting metrics from MySQL master...")
    data = extract_all(engine)

    print("Step 2: Uploading to Cloud Firestore...")
    counts = upload_all(db, data)
    for col, count in counts.items():
        print(f"  - {col:<26}: {count} documents")

    print(f"All collections uploaded successfully in {time.time()-t0:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
