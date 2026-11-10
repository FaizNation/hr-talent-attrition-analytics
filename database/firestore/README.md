# Cloud Firestore — Read-Optimized NoSQL Serving Layer

This directory manages the **NoSQL Query Serving Layer** using **Google Cloud Firestore** for the **Workforce Cost & Startup Runway Simulator** project.

---

## 1. Architectural Role (Polyglot Persistence)

The project separates concerns between transactional master storage and high-speed query serving:

```
+------------------------------------+
|  MySQL 8.0 (db_hr_mnc)             |
|  System of Record / Source of Truth|
|  - hr_employee (2,000,000 raw rows)|
|  - 4 Dimension tables (3NF)        |
+------------------------------------+
                  │
                  ▼ ETL Aggregation (`upload_to_firestore.py`)
+------------------------------------+
|  Cloud Firestore (hr-mnc-database) |
|  Read-Optimized Serving Layer      |
|  - Pre-aggregated documents        |
|  - Zero joins, O(1) latency        |
+------------------------------------+
                  │
                  ▼ Fast Query Reads (< 100ms)
+------------------------------------+
|  Frontend & API Simulator          |
|  (Interactive Dashboard)          |
+------------------------------------+
```

- **MySQL (`db_hr_mnc`)**: Holds the full 2,000,000 raw employee records in a strictly normalized schema.
- **Cloud Firestore (`hr-mnc-database`)**: Serves pre-computed metrics and benchmarks for instant dashboard loading without taxing the relational database with multi-second aggregate scans.

---

## 2. Collections & Documents

| Collection | Doc ID | Document Count | Purpose |
|---|---|---:|---|
| `department_benchmarks` | Department Name (e.g. `IT`, `Finance`, `Sales`) | 7 | Headcount, cost category, and average salary per department |
| `role_benchmarks` | Slugified Job Title (e.g. `software_engineer`) | 29 | Market median salary, bounds, and average experience for 29 roles |
| `work_mode_profiles` | Work Mode (`on_site`, `remote`) | 2 | Workforce distribution and cost overhead factors (1.20x vs 1.03x) |
| `startup_stage_presets` | Stage (`seed`, `series_a`, `series_b`) | 3 | Baseline cash balance, revenue, and OpEx ratios per startup stage |

### Privacy & Data Protection Boundary
- **Zero PII**: No employee names (`full_name`) or personal IDs (`employee_id`) are uploaded to Firestore.
- Firestore holds exclusively aggregate distributions, market medians, and business parameters.

---

## 3. Prerequisites & Setup

### Dependencies
Install the required packages:
```bash
python -m pip install firebase-admin google-cloud-firestore SQLAlchemy PyMySQL python-dotenv
```

### Credentials
1. Copy `.env.example` to `.env`:
   ```bash
   cd database/firestore
   copy .env.example .env
   ```
2. Configure `.env`:
   ```dotenv
   FIREBASE_CREDENTIALS_PATH=hr-mnc-database-firebase-adminsdk-fbsvc-5b06852598.json
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=
   DB_NAME=db_hr_mnc
   ```
*(Note: `.env` and service account `.json` files are git-ignored; never commit secrets).*

---

## 4. Execution Workflow

All scripts are executed from `database/firestore/`:

### 1. Test Aggregation Extraction (Dry Run)
Extracts metrics from MySQL without writing to Firestore:
```bash
python extract_from_mysql.py
```
*Expected: 7 departments, 29 roles, 2 work modes, 3 presets; total headcount = 2,000,000.*

### 2. Upload Documents to Firestore
Performs atomic batched writes to Cloud Firestore:
```bash
python upload_to_firestore.py
```
*Expected: Submits 41 documents in a single atomic batch commit to `hr-mnc-database`.*

### 3. Verify Live Queries
Executes read queries against all collections and validates business invariants:
```bash
python verify_firestore.py
```
*Expected: All 4 collections verified, O(1) read test passes, `FINAL RESULT: PASS`.*

---

## 5. Security Rules (Cloud Firestore)

In the Firebase Console (**Firestore Database → Rules** tab):

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Read-only access for public dashboard clients; writes restricted to Admin SDK
    match /{document=**} {
      allow read: if true;
      allow write: if false;
    }
  }
}
```
Client applications have read-only access, while backend scripts write securely via the Firebase Admin SDK.
