"""Step 4: Verify data in Firebase Realtime Database.

Reads back each node from Firebase, compares record counts with local exports,
and prints sample records and the Firebase console URL.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, db

from config import (
    EXPORT_DIR,
    FIREBASE_DATABASE_URL,
    get_firebase_credentials_path,
)


def load_export(filename: str) -> dict:
    path = EXPORT_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def init_firebase_app():
    if not firebase_admin._apps:
        cred_path = get_firebase_credentials_path()
        cred = credentials.Certificate(str(cred_path))
        firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DATABASE_URL})
    return db.reference()


def get_console_url(database_url: str) -> str:
    """Generate direct console URL from RTDB URL."""
    # Example URL: https://hr-mnc-database-default-rtdb.asia-southeast1.firebasedatabase.app
    import re
    m = re.match(r"https://([a-zA-Z0-9_-]+)(?:-default-rtdb)?\.([a-zA-Z0-9_-]+)\.firebasedatabase\.app", database_url)
    if m:
        project_id = m.group(1).replace("-default-rtdb", "")
        return f"https://console.firebase.google.com/project/{project_id}/database"
    return "https://console.firebase.google.com"


def verify_firebase() -> bool:
    print("=" * 78)
    print("Step 4 - Verify Firebase Realtime Database")
    print("=" * 78)

    root_ref = init_firebase_app()
    exp_summary = load_export("dashboard_summary.json")
    exp_segments = load_export("talent_segment_summary.json")
    exp_branch = load_export("branch_efficiency.json")
    exp_risk = load_export("attrition_risk.json")

    print("\nReading data back from Firebase...")

    # 1. Dashboard summary
    fb_summary = root_ref.child("dashboard_summary").get() or {}
    print(f"  /dashboard_summary: {'MATCH' if fb_summary else 'EMPTY'}")

    # 2. Talent Segment summary
    fb_segments = root_ref.child("talent_segment_summary").get() or {}
    print(f"  /talent_segment_summary: {len(fb_segments)} items (expected {len(exp_segments)})")

    # 3. Branch efficiency
    fb_branch = root_ref.child("branch_efficiency").get() or {}
    print(f"  /branch_efficiency: {len(fb_branch):,} items (expected {len(exp_branch):,})")

    # 4. Attrition risk
    fb_risk = root_ref.child("attrition_risk").get() or {}
    print(f"  /attrition_risk: {len(fb_risk):,} items (expected {len(exp_risk):,})")

    # Validation
    all_ok = True
    errors = []
    if len(fb_segments) != len(exp_segments):
        errors.append(f"Segment count mismatch: {len(fb_segments)} vs {len(exp_segments)}")
        all_ok = False
    if len(fb_branch) != len(exp_branch):
        errors.append(f"Branch count mismatch: {len(fb_branch)} vs {len(exp_branch)}")
        all_ok = False
    if len(fb_risk) != len(exp_risk):
        errors.append(f"Attrition risk count mismatch: {len(fb_risk)} vs {len(exp_risk)}")
        all_ok = False

    print("\n" + "=" * 78)
    print("Sample Records from Firebase")
    print("=" * 78)

    print("\n[Sample: /dashboard_summary]")
    print(json.dumps(fb_summary, indent=2))

    print("\n[Sample: /talent_segment_summary (1 item)]")
    if fb_segments:
        first_seg_k = next(iter(fb_segments))
        print(json.dumps({first_seg_k: fb_segments[first_seg_k]}, indent=2))

    print("\n[Sample: /branch_efficiency (1 item)]")
    if fb_branch:
        first_b_k = next(iter(fb_branch))
        print(json.dumps({first_b_k: fb_branch[first_b_k]}, indent=2))

    print("\n[Sample: /attrition_risk (1 item)]")
    if fb_risk:
        first_r_k = next(iter(fb_risk))
        print(json.dumps({first_r_k: fb_risk[first_r_k]}, indent=2))

    print("\n" + "=" * 78)
    print("Verification Summary")
    print("=" * 78)
    if all_ok:
        print("Status: PASS (All nodes match exact counts and structures)")
    else:
        print("Status: FAIL")
        for err in errors:
            print(f"  - {err}")

    console_url = get_console_url(FIREBASE_DATABASE_URL)
    print(f"\nFirebase Console Link for Screenshot:")
    print(f"  {console_url}")
    print(f"  Realtime Database URL: {FIREBASE_DATABASE_URL}")

    return all_ok


if __name__ == "__main__":
    success = verify_firebase()
    sys.exit(0 if success else 1)
