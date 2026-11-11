# MongoDB — Full-Scale NoSQL Layer & Native Summaries

This directory manages the **Local NoSQL Database Layer** using **MongoDB 8.2 (`db_hr_mnc`)** for the **HR MNC Dataset & Analytics** project.

While Cloud Firestore serves as the quota-safe cloud demo (summaries + 500 samples), MongoDB serves as the **Full-Scale 2,000,000 Document Store & Aggregation Engine**.

---

## 1. Architectural Role (Polyglot Persistence)

```
+------------------------------------+
|  MySQL 8.0 (db_hr_mnc)             |
|  System of Record / Relational 3NF |
|  - hr_employee (2,000,000 raw rows)|
|  - 4 Dimension tables              |
+------------------------------------+
                  │
                  ▼ Chunked Streaming (`load_mysql_to_mongodb.py`)
+------------------------------------+
|  MongoDB 8.2 (localhost:27017)     |
|  Database: db_hr_mnc               |
|  - employees (2,000,000 documents) |
|  - Secondary Indexes               |
+------------------------------------+
                  │
                  ▼ Native Aggregation Pipelines (`generate_summaries.py`)
+------------------------------------+
|  Analytical Summary Collections    |
|  - hr_overview_summary (1 doc)     |
|  - department_summary (7 docs)     |
|  - job_title_summary (29 docs)     |
|  - work_mode_summary (2 docs)      |
+------------------------------------+
```

---

## 2. Collections in MongoDB (`db_hr_mnc`)

| Collection | Expected Documents | Description |
|---|---:|---|
| **`employees`** | **2,000,000** | Full raw dataset converted into native BSON documents (`_id` = `employee_id`) |
| **`hr_overview_summary`** | **1** | Macro organization metrics (total headcount, total payroll, salary bounds, status & work mode distribution) |
| **`department_summary`** | **7** | Department analytics (headcount, share %, total payroll, avg salary, avg performance/experience) |
| **`job_title_summary`** | **29** | Job title analytics (headcount, min/avg/max salary, avg experience) |
| **`work_mode_summary`** | **2** | Work mode analytics (On-site vs Remote headcount, avg salary, avg rating) |

### Secondary Indexes on `employees`
To ensure lightning-fast queries across 2,000,000 records, the loader builds 5 secondary B-tree indexes:
- `department`: 1
- `job_title`: 1
- `status`: 1
- `work_mode`: 1
- `salary_inr`: 1

---

## 3. Setup & Prerequisites

### Requirements
- Python 3.10+
- PyMongo (`pip install pymongo`)
- MongoDB Server running locally on port 27017 (`mongodb://localhost:27017/`)
- MongoDB Compass (recommended for visual GUI demonstration)

### Configuration
1. Copy `.env.example` to `.env`:
   ```bash
   cd database/mongodb
   copy .env.example .env
   ```
2. Default connection values in `.env`:
   ```dotenv
   MONGO_URI=mongodb://localhost:27017/
   MONGO_DB_NAME=db_hr_mnc
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=
   DB_NAME=db_hr_mnc
   ```

---

## 4. Execution Workflow

All scripts are executed from `database/mongodb/`:

### Step 1: Stream 2,000,000 Records from MySQL to MongoDB
```bash
python load_mysql_to_mongodb.py
```
*Expected: Streams rows in 50,000-row chunks (~22,000 docs/s). Takes ~90 seconds to load all 2,000,000 documents and build secondary indexes.*

### Step 2: Generate Summaries via Native Aggregation Pipelines
```bash
python generate_summaries.py
```
*Expected: Executes native `$group` and `$facet` aggregation pipelines directly in MongoDB engine. Completes in ~30 seconds.*

### Step 3: Run Live Verification
```bash
python verify_mongodb.py
```
*Expected: Verifies document counts across all 5 collections (2M, 7, 29, 2, 1), indexes, business invariants, and sub-millisecond query latency. Exits with code 0.*

---

## 5. Visual Demonstration in MongoDB Compass

You can view and inspect the entire 2,000,000-record dataset visually:

1. Open **MongoDB Compass**.
2. Paste the connection string:
   ```
   mongodb://localhost:27017/
   ```
   and click **Connect**.
3. In the left sidebar, click on database **`db_hr_mnc`**.
4. You will see all 5 collections:
   - Click on **`employees`**: It will display `Total documents: 2,000,000`.
   - Click on **`department_summary`**: Displays 7 documents with headcount and payroll breakdowns.
   - Click on **`hr_overview_summary`**: Displays the global macro summary.
5. In the **Filter** bar of `employees`, try these fast indexed queries:
   - High-performing IT staff:
     ```json
     { "department": "IT", "performance_rating": { "$gte": 4 } }
     ```
   - Employees earning above INR 2,500,000:
     ```json
     { "salary_inr": { "$gte": 2500000 } }
     ```
   - Resigned Remote employees:
     ```json
     { "status": "Resigned", "work_mode": "Remote" }
     ```
   Results return instantly (in < 5ms).
