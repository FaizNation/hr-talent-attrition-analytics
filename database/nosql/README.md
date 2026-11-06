# HR Talent Analytics - NoSQL Pipeline (Firebase Realtime Database)

This folder contains the complete NoSQL pipeline for delivering analytics data to the frontend application via Firebase Realtime Database.

---

## 1. Architectural Roles

- **MySQL (`db_hr_mnc`)**:
  - Acts as the primary analytical relational database.
  - Holds 2,000,000 raw employee records (`hr_attrition`), 2,000,000 engineered features (`hr_features`), and 3,402 aggregate branch records (`branch_efficiency`).
  - Performs heavy aggregations, joins, and analytical computations.
- **Firebase Realtime Database**:
  - Serves as the high-availability, low-latency NoSQL data layer consumed directly by the web/mobile app.
  - Holds pre-computed dashboard KPIs, segment summaries, branch performance cards, and the top 2,000 at-risk talent profiles.

---

## 2. Firebase Database Structure

```text
/
├── dashboard_summary
│   ├── total_employees: 2000000
│   ├── underpaid_count: 782571
│   ├── underpaid_pct: 39.1286
│   ├── high_flight_risk_count: 218778
│   ├── lost_star_count: 199279
│   └── generated_at: "2026-11-06T..."
│
├── talent_segment_summary
│   ├── standard_low_perf: { segment, total: 1239540, percentage: 61.977 }
│   ├── stable_workforce: { segment, total: 342403, percentage: 17.1202 }
│   ├── high_flight_risk: { segment, total: 218778, percentage: 10.9389 }
│   └── lost_star_talent: { segment, total: 199279, percentage: 9.964 }
│
├── branch_efficiency
│   └── {country}_{department}_{work_mode} (3,402 nodes)
│       ├── country
│       ├── department
│       ├── work_mode
│       ├── total_employees
│       ├── attrition_count
│       ├── turnover_rate_pct
│       ├── avg_salary_disparity
│       └── avg_performance
│
└── attrition_risk
    └── {employee_id} (Top 2,000 highest risk nodes)
        ├── employee_id
        ├── country
        ├── city
        ├── department
        ├── job_title
        ├── salary_disparity_index
        ├── tenure_years
        ├── performance_to_exp_ratio
        ├── talent_segment
        └── risk_score: null (ranked by lowest SDI among High Flight Risk)
```

---

## 3. Run Order

Run all commands from `database/nosql/`:

```bash
# 1. Extract aggregated datasets from MySQL into database/nosql/export/
python extract_from_mysql.py

# 2. Test payloads and credentials in dry-run mode (read-only, no writes)
python upload_to_firebase.py --dry-run

# 3. Perform idempotent upload in 500-record batches to Firebase
python upload_to_firebase.py

# 4. Read back and verify all counts, structures, and sample values
python verify_firebase.py
```

---

## 4. Security Rules (Realtime Database)

In the Firebase Console (**Realtime Database → Rules** tab), paste:

```json
{
  "rules": {
    ".read": true,
    ".write": false
  }
}
```

- **`.read: true`**: Allows frontend apps to fetch dashboard charts and tables without embedding admin service credentials.
- **`.write: false`**: Rejects all client write attempts. Only backend scripts authenticated via Firebase Admin SDK (service account) can write.
