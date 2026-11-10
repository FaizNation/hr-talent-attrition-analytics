# Firestore Read-Optimized Query Layer Design

Date: 2026-11-10
Status: proposed (awaiting user approval)

## Intent

Implement a **Polyglot Persistence / Read-Optimized Serving Layer** using **Google Cloud Firestore**, fulfilling the architectural requirement:
- **MySQL (`db_hr_mnc`)**: Primary data store / *System of Record* holding 2,000,000 normalized raw rows (`hr_employee` + 4 dimensions).
- **Cloud Firestore (`hr-mnc-database`)**: High-speed NoSQL *Query Serving Layer* holding pre-aggregated, denormalized documents for the Workforce Cost & Startup Runway Simulator dashboard.

---

## Approaches Considered

1. **Approach A: Firebase Realtime Database (JSON Tree)**
   - *Pros:* Simple tree structure; previously used in the old attrition version.
   - *Cons:* Limited querying, lack of collection/document indexing semantics, harder to scale granular document updates.
2. **Approach B: Cloud Firestore (Collection & Document Mode) — [CHOSEN]**
   - *Pros:* Native NoSQL document database, sub-second queries, rich filtering/indexing, native batch writes, already activated and accessible in Google Cloud project `hr-mnc-database` via service account.
   - *Cons:* Requires document modeling for runway metrics.
3. **Approach C: Local MongoDB**
   - *Pros:* Self-hosted document database.
   - *Cons:* Requires installing new local services/daemons on the developer machine; not cloud-accessible by frontend without custom hosting.

**Decision:** Approach B (Cloud Firestore) selected by user.

---

## Firestore Schema & Collections

Firestore project: `hr-mnc-database`

### Collection 1: `department_benchmarks` (7 documents)
Document ID: department name (e.g. `IT`, `Finance`, `Sales`, `HR`, `Marketing`, `R&D`, `Operations`)
```json
{
  "department": "IT",
  "employee_count": 285400,
  "headcount_percentage": 14.27,
  "avg_salary_inr": 1850400.0,
  "min_salary_inr": 300000,
  "max_salary_inr": 2999976,
  "cost_category": "R&D / Product Spend",
  "updated_at": "TIMESTAMP"
}
```

### Collection 2: `role_benchmarks` (29 documents)
Document ID: slugified job title (e.g. `software_engineer`, `data_scientist`, `product_manager`)
```json
{
  "job_title": "Software Engineer",
  "department": "IT",
  "employee_count": 68900,
  "market_median_salary_inr": 1820000.0,
  "min_salary_inr": 300000,
  "max_salary_inr": 2999500,
  "avg_salary_inr": 1845000.0,
  "avg_experience_years": 7.5,
  "avg_performance_rating": 3.0,
  "updated_at": "TIMESTAMP"
}
```

### Collection 3: `work_mode_profiles` (2 documents)
Document ID: work mode (e.g. `On-site`, `Remote`)
```json
{
  "work_mode": "On-site",
  "employee_count": 1000500,
  "share_percentage": 50.02,
  "avg_salary_inr": 1825000.0,
  "overhead_factor": 1.20,
  "description": "Requires office facility & physical infrastructure overhead (1.20x)",
  "updated_at": "TIMESTAMP"
}
```

### Collection 4: `startup_stage_presets` (3 documents)
Document ID: stage name (e.g. `Seed`, `Series_A`, `Series_B`)
```json
{
  "stage": "Seed",
  "initial_cash_balance_inr": 35000000.0,
  "monthly_revenue_inr": 300000.0,
  "revenue_growth_rate": 0.06,
  "rd_spend_ratio": 0.55,
  "admin_spend_ratio": 0.15,
  "marketing_spend_ratio": 0.30,
  "non_payroll_opex_ratio": 0.25,
  "updated_at": "TIMESTAMP"
}
```

---

## ETL Pipeline Architecture (`database/firestore/`)

1. `config.py`: Centralized credentials loader from `.env` (`FIREBASE_CREDENTIALS_PATH`, MySQL settings).
2. `extract_from_mysql.py`: Aggregates the 2,000,000 rows from MySQL `hr_employee` + 4 dimensions into clean JSON-serializable payloads.
3. `upload_to_firestore.py`: Uses `google-cloud-firestore` / `firebase-admin` batch writer (`batch.set(doc_ref, data)`) to push all collections idempotently.
4. `verify_firestore.py`: Executes read queries against Firestore, asserts document counts (7, 29, 2, 3) and fields, printing PASS/FAIL.
5. `README.md`: Clear documentation of the NoSQL layer and its relationship with the MySQL master.

---

## Security & Access
- Writes are performed exclusively by backend admin scripts using service account credentials.
- Firestore Security Rules enforce read-only access for client applications (`allow write: if false; allow read: if true;`).
