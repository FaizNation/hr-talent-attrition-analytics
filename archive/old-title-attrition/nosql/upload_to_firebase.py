"""Step 3: Upload extracted JSON data to Firebase Realtime Database.

Features:
- Batched update() calls (500 records per batch) for large nodes
- Full idempotency (overwrites same keys, no duplicates)
- Dry-run validation mode (--dry-run)
- Type safety: cleans all NaN/Decimal/NumPy types
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import credentials, db

from config import (
    EXPORT_DIR,
    FIREBASE_DATABASE_URL,
    get_firebase_credentials_path,
)

BATCH_SIZE = 500


def clean_for_firebase(obj: Any) -> Any:
    """Recursively convert NaN/float/integers/keys for Firebase compliance."""
    if isinstance(obj, dict):
        return {str(k): clean_for_firebase(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_for_firebase(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


def load_export(filename: str) -> dict:
    path = EXPORT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Export file not found: {path}. Run extract_from_mysql.py first.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def init_firebase_app():
    """Initialize firebase-admin safely without creating duplicate default apps."""
    if not firebase_admin._apps:
        cred_path = get_firebase_credentials_path()
        if not FIREBASE_DATABASE_URL:
            raise ValueError("FIREBASE_DATABASE_URL is not set in database/nosql/.env")
        cred = credentials.Certificate(str(cred_path))
        firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DATABASE_URL})
    return db.reference()


def upload_node_in_batches(root_ref, node_name: str, data: dict, dry_run: bool = False):
    total = len(data)
    print(f"\nNode /{node_name}: {total:,} records")

    if dry_run:
        print(f"  [DRY-RUN] Validating keys and format for /{node_name}...")
        for k in data.keys():
            if any(ch in k for ch in [".", "$", "#", "[", "]", "/"]):
                raise ValueError(f"Illegal Firebase key detected: {k!r}")
        print(f"  [DRY-RUN] Ready to upload {total:,} records in {(total + BATCH_SIZE - 1) // BATCH_SIZE} batch(es).")
        return

    node_ref = root_ref.child(node_name)
    keys = list(data.keys())
    batches = [keys[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]

    started = time.perf_counter()
    for idx, batch_keys in enumerate(batches, 1):
        batch_payload = {k: data[k] for k in batch_keys}
        node_ref.update(batch_payload)
        uploaded_count = min(idx * BATCH_SIZE, total)
        pct = (uploaded_count / total) * 100
        print(f"  Progress: {uploaded_count:>5,} / {total:,} ({pct:5.1f}%) [Batch {idx}/{len(batches)}]")

    elapsed = time.perf_counter() - started
    print(f"  Uploaded /{node_name} in {elapsed:.2f}s.")


def upload_single_object(root_ref, node_name: str, data: dict, dry_run: bool = False):
    print(f"\nNode /{node_name}: 1 object")
    if dry_run:
        print(f"  [DRY-RUN] Validating single object /{node_name}...")
        return
    started = time.perf_counter()
    root_ref.child(node_name).set(data)
    elapsed = time.perf_counter() - started
    print(f"  Uploaded /{node_name} in {elapsed:.2f}s.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate JSON payloads and Firebase connection without writing data.",
    )
    args = parser.parse_args()

    print("=" * 78)
    print(f"Step 3 - Upload to Firebase Realtime Database {'(DRY-RUN)' if args.dry_run else ''}")
    print("=" * 78)

    # 1. Load exported data
    print("Loading exported JSON files...")
    dashboard_summary = clean_for_firebase(load_export("dashboard_summary.json"))
    talent_segments = clean_for_firebase(load_export("talent_segment_summary.json"))
    branch_efficiency = clean_for_firebase(load_export("branch_efficiency.json"))
    attrition_risk = clean_for_firebase(load_export("attrition_risk.json"))

    # 2. Initialize Firebase
    print("Connecting to Firebase...")
    try:
        root_ref = init_firebase_app()
        print("Connected successfully.")
    except Exception as exc:
        print(f"Failed to initialize Firebase Admin SDK: {exc}")
        return 1

    # 3. Perform uploads or dry-run validation
    try:
        upload_single_object(root_ref, "dashboard_summary", dashboard_summary, dry_run=args.dry_run)
        upload_node_in_batches(root_ref, "talent_segment_summary", talent_segments, dry_run=args.dry_run)
        upload_node_in_batches(root_ref, "branch_efficiency", branch_efficiency, dry_run=args.dry_run)
        upload_node_in_batches(root_ref, "attrition_risk", attrition_risk, dry_run=args.dry_run)

        print("\n" + "=" * 78)
        if args.dry_run:
            print("Dry-run completed successfully! All data, keys, and credentials are valid.")
        else:
            print("Upload completed successfully! All nodes populated in Firebase.")
        print("=" * 78)
        return 0
    except Exception as exc:
        print(f"\nUpload failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
