# Cloud Firestore — HR Summary & NoSQL Serving Layer

This directory manages the **NoSQL Serving Layer** using **Google Cloud Firestore (`hr-mnc-database`)** for the **HR MNC Dataset & Analytics** project.

---

## 1. Architectural Role (Polyglot Persistence)

The project separates concerns between relational master storage and high-speed NoSQL query serving:

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
|  - Pre-aggregated HR summaries    |
|  - Denormalized employee samples   |
|  - Zero joins, sub-100ms O(1) reads|
+------------------------------------+
                  │
                  ▼ Fast Query Reads (< 100ms)
+------------------------------------+
|  Frontend & Client Consumers       |
|  (Interactive Dashboard / Reports) |
+------------------------------------+
```

- **MySQL (`db_hr_mnc`)**: Holds the complete 2,000,000 raw records in a strictly normalized relational schema.
- **Cloud Firestore (`hr-mnc-database`)**: Directly converts and stores pre-computed analytical summaries and sample documents for instant dashboard retrieval without running expensive multi-second table scans on MySQL.

---

## 2. Collections & Document Schemas

All collections are derived 100% from the HR dataset:

| Collection | Doc ID | Document Count | Purpose |
|---|---|---:|---|
| `hr_overview_summary` | `global` | 1 | Macro organizational metrics: 2M headcount, total payroll, salary bounds, status & work mode distribution |
| `department_summary` | Department Name (e.g. `IT`, `Finance`, `Sales`) | 7 | Headcount, share %, total payroll, avg salary, and experience/performance ratings per department |
| `job_title_summary` | Slugified Job Title (e.g. `software_engineer`) | 29 | Headcount, avg salary, min/max salary, and average experience across 29 roles |
| `work_mode_summary` | Work Mode (`on_site`, `remote`) | 2 | Headcount, share %, avg salary, and avg rating comparison between work modes |
| `employee_sample` | `employee_id` (e.g. `EMP0000001`) | 500 | Denormalized employee document records demonstrating direct NoSQL document conversion |

### Privacy & Data Protection Boundary
- **Zero PII**: Employee personal names (`full_name`) are strictly excluded from the `employee_sample` collection to ensure privacy compliance.

---

## 3. Setup & Prerequisites

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
Extracts summary metrics from MySQL without writing to Firestore:
```bash
python extract_from_mysql.py
```
*Expected: 1 overview, 7 departments, 29 job titles, 2 work modes, 500 employee samples; total headcount = 2,000,000.*

### 2. Upload Documents to Firestore
Purges any legacy non-HR collections and performs chunked atomic batch writes (< 500 ops) to Cloud Firestore:
```bash
python upload_to_firestore.py
```
*Expected: Purges legacy collections; submits 539 documents in 2 chunked batches to `hr-mnc-database`.*

### 3. Verify Live Queries
Executes read queries against all collections and validates business invariants:
```bash
python verify_firestore.py
```
*Expected: All 5 collections verified, legacy collections verified 0 docs, O(1) read test passes, `FINAL RESULT: PASS`.*

---

## 5. Security Rules (Cloud Firestore)

In the Firebase Console (**Firestore Database → Rules** tab):

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Read-only access for client applications; writes restricted to Admin SDK
    match /{document=**} {
      allow read: if true;
      allow write: if false;
    }
  }
}
```
Client applications have read-only access, while backend scripts write securely via the Firebase Admin SDK.
