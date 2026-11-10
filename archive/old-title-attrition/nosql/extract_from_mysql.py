"""Step 2: Extract aggregate and risk data from MySQL into clean JSON files.

Runs fast aggregate queries against hr_features and branch_efficiency.
Verifies results against known project constants.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from decimal import Decimal

import pandas as pd
from sqlalchemy import text

from config import EXPORT_DIR, get_mysql_engine

# Firebase Key sanitizer
INVALID_KEY_PATTERN = re.compile(r'[^A-Za-z0-9_-]+')


def sanitize_key(value: str) -> str:
    """Sanitize string to be safe as a Firebase Realtime Database path key."""
    clean = INVALID_KEY_PATTERN.sub('_', str(value).strip()).strip('_')
    return clean or "item"


SEGMENT_KEY_MAP = {
    "Standard / Low Perf": "standard_low_perf",
    "Stable Workforce": "stable_workforce",
    "High Flight Risk (Underpaid Star)": "high_flight_risk",
    "Lost Star Talent": "lost_star_talent",
}


def serialize_val(val):
    """Ensure decimals, timestamps, or numpy values are JSON-serializable."""
    if isinstance(val, Decimal):
        return float(val)
    if pd.isna(val):
        return None
    if hasattr(val, "item"):
        return val.item()
    return val


def clean_dict(d: dict) -> dict:
    return {k: serialize_val(v) for k, v in d.items()}


def extract_data() -> dict:
    engine = get_mysql_engine()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    now_utc = datetime.now(timezone.utc).isoformat()

    print("=" * 78)
    print("Step 2 - Extracting data from MySQL")
    print("=" * 78)

    with engine.connect() as conn:
        # 1. Dashboard summary
        print("\n1. Querying dashboard_summary...")
        summary_query = text("""
            SELECT
                COUNT(*) AS total_employees,
                SUM(salary_disparity_index < 0.9) AS underpaid_count,
                ROUND(100.0 * SUM(salary_disparity_index < 0.9) / COUNT(*), 4) AS underpaid_pct,
                SUM(talent_segment = 'High Flight Risk (Underpaid Star)') AS high_flight_risk_count,
                SUM(talent_segment = 'Lost Star Talent') AS lost_star_count
            FROM hr_features
        """)
        sum_row = conn.execute(summary_query).mappings().one()
        dashboard_summary = {
            "total_employees": int(sum_row["total_employees"]),
            "underpaid_count": int(sum_row["underpaid_count"]),
            "underpaid_pct": float(sum_row["underpaid_pct"]),
            "high_flight_risk_count": int(sum_row["high_flight_risk_count"]),
            "lost_star_count": int(sum_row["lost_star_count"]),
            "generated_at": now_utc,
        }

        # 2. Talent Segment summary
        print("2. Querying talent_segment_summary...")
        seg_query = text("""
            SELECT
                talent_segment,
                COUNT(*) AS total,
                ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM hr_features), 4) AS percentage
            FROM hr_features
            GROUP BY talent_segment
            ORDER BY total DESC
        """)
        seg_rows = conn.execute(seg_query).mappings().all()
        talent_segment_summary = {}
        for r in seg_rows:
            seg_name = r["talent_segment"]
            seg_key = SEGMENT_KEY_MAP.get(seg_name, sanitize_key(seg_name))
            talent_segment_summary[seg_key] = {
                "segment": seg_name,
                "total": int(r["total"]),
                "percentage": float(r["percentage"]),
            }

        # 3. Branch efficiency
        print("3. Querying branch_efficiency (3,402 rows)...")
        branch_query = text("""
            SELECT
                country,
                department,
                work_mode,
                total_employees,
                attrition_count,
                turnover_rate_pct,
                avg_salary_disparity,
                avg_performance
            FROM branch_efficiency
            ORDER BY country, department, work_mode
        """)
        branch_rows = conn.execute(branch_query).mappings().all()
        branch_efficiency = {}
        for r in branch_rows:
            raw_key = f"{r['country']}_{r['department']}_{r['work_mode']}"
            b_key = sanitize_key(raw_key)
            branch_efficiency[b_key] = {
                "country": r["country"],
                "department": r["department"],
                "work_mode": r["work_mode"],
                "total_employees": int(r["total_employees"]),
                "attrition_count": int(r["attrition_count"]),
                "turnover_rate_pct": float(r["turnover_rate_pct"]),
                "avg_salary_disparity": float(r["avg_salary_disparity"]),
                "avg_performance": float(r["avg_performance"]),
            }

        # 4. Attrition risk (Top 2,000 employees)
        print("4. Querying top 2,000 attrition risk employees...")
        risk_query = text("""
            SELECT
                employee_id,
                country,
                city,
                department,
                job_title,
                salary_disparity_index,
                tenure_years,
                performance_to_exp_ratio,
                talent_segment
            FROM hr_features
            WHERE talent_segment = 'High Flight Risk (Underpaid Star)'
            ORDER BY salary_disparity_index ASC, employee_id ASC
            LIMIT 2000
        """)
        risk_rows = conn.execute(risk_query).mappings().all()
        attrition_risk = {}
        for r in risk_rows:
            emp_id = sanitize_key(r["employee_id"])
            attrition_risk[emp_id] = {
                "employee_id": r["employee_id"],
                "country": r["country"],
                "city": r["city"],
                "department": r["department"],
                "job_title": r["job_title"],
                "salary_disparity_index": float(r["salary_disparity_index"]),
                "tenure_years": int(r["tenure_years"]),
                "performance_to_exp_ratio": float(r["performance_to_exp_ratio"]),
                "talent_segment": r["talent_segment"],
                "risk_score": None,  # Placeholder indicator
            }

    # Save to export files
    files = {
        "dashboard_summary.json": dashboard_summary,
        "talent_segment_summary.json": talent_segment_summary,
        "branch_efficiency.json": branch_efficiency,
        "attrition_risk.json": attrition_risk,
    }

    for fname, payload in files.items():
        out_path = EXPORT_DIR / fname
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Wrote {out_path.name} ({out_path.stat().st_size:,} bytes)")

    # 5. Verification checks
    print("\n" + "=" * 78)
    print("Verification against known values")
    print("=" * 78)

    errors = []
    if dashboard_summary["total_employees"] != 2_000_000:
        errors.append(f"Total employees mismatch: {dashboard_summary['total_employees']} != 2,000,000")
    if dashboard_summary["high_flight_risk_count"] != 218_778:
        errors.append(f"High Flight Risk count mismatch: {dashboard_summary['high_flight_risk_count']} != 218,778")
    if dashboard_summary["lost_star_count"] != 199_279:
        errors.append(f"Lost Star count mismatch: {dashboard_summary['lost_star_count']} != 199,279")

    seg_sum = sum(s["total"] for s in talent_segment_summary.values())
    if seg_sum != 2_000_000:
        errors.append(f"Talent segment sum mismatch: {seg_sum} != 2,000,000")

    if len(branch_efficiency) != 3_402:
        errors.append(f"Branch efficiency count mismatch: {len(branch_efficiency)} != 3,402")

    if len(attrition_risk) != 2_000:
        errors.append(f"Attrition risk count mismatch: {len(attrition_risk)} != 2,000")

    if errors:
        print("FAILED checks:")
        for err in errors:
            print(f"  - {err}")
        return False

    print("ALL CHECKS PASSED:")
    print(f"  - total_employees        : {dashboard_summary['total_employees']:,} (OK)")
    print(f"  - underpaid_count        : {dashboard_summary['underpaid_count']:,} ({dashboard_summary['underpaid_pct']}%)")
    print(f"  - high_flight_risk_count : {dashboard_summary['high_flight_risk_count']:,} (OK)")
    print(f"  - lost_star_count        : {dashboard_summary['lost_star_count']:,} (OK)")
    print(f"  - segment sum            : {seg_sum:,} across {len(talent_segment_summary)} segments (OK)")
    print(f"  - branch_efficiency rows : {len(branch_efficiency):,} (OK, 0 collisions)")
    print(f"  - attrition_risk rows    : {len(attrition_risk):,} (OK)")
    return True


if __name__ == "__main__":
    success = extract_data()
    sys.exit(0 if success else 1)
