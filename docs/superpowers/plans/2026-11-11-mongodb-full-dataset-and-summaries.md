# MongoDB Full Dataset & Summary Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a high-performance local NoSQL database layer using MongoDB 8.2, storing the full 2,000,000 normalized employee records and native aggregation summaries in database `db_hr_mnc`.

**Architecture:** Polyglot persistence. MySQL (`db_hr_mnc`) serves as the relational single source of truth. A streaming Python loader extracts 2,000,000 records from `hr_employee` in 50,000-row chunks and loads them into MongoDB collection `employees` (`_id` = `employee_id`). MongoDB native aggregation pipelines then compute and persist 4 analytical summary collections.

**Tech Stack:** Python 3.10, PyMongo 4.18, MongoDB 8.2 (Windows Service, port 27017), SQLAlchemy, PyMySQL, MySQL 8.0.

**Spec:** `docs/superpowers/specs/2026-11-11-mongodb-full-dataset-and-summaries-design.md`

## Global Constraints

- Full scale: `employees` collection in MongoDB must hold exactly 2,000,000 documents.
- Summary collections must be derived directly from MongoDB `employees` using native aggregation pipelines:
  - `hr_overview_summary` (1 document)
  - `department_summary` (7 documents)
  - `job_title_summary` (29 documents)
  - `work_mode_summary` (2 documents)
- Database credentials loaded via `.env` (defaults: `mongodb://localhost:27017/` and MySQL `db_hr_mnc`).
- Idempotent and resume-safe: re-running scripts must not duplicate documents or fail with key errors.

## Review Focus

- Memory exhaustion during 2M row streaming: must use chunked pagination (`row_id` slices) rather than loading 2M rows into Python RAM at once.
- Index creation order: create indexes after batch insertion to maximize write throughput.
- Zero orphan values in summary aggregates: sum of `employee_count` in `department_summary` and in `work_mode_summary` must strictly equal 2,000,000.
- Date serialization: convert MySQL `DATE` objects to ISO string or `datetime.datetime` for proper BSON storage.
- Re-run safety: loader must detect if `employees` already holds 2,000,000 documents and skip re-insertion gracefully.

---

### Task 1: Package Scaffolding & Configuration

**Files:**
- Create: `database/mongodb/config.py`
- Create: `database/mongodb/.env.example`

**Interfaces:**
- Produces: `get_mongo_client() -> MongoClient`, `get_mongo_db() -> Database`, `get_mysql_engine() -> Engine`.

- [ ] **Step 1: Create `database/mongodb/.env.example`**

Include: `MONGO_URI=mongodb://localhost:27017/`, `MONGO_DB_NAME=db_hr_mnc`, plus MySQL connection settings (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`).

- [ ] **Step 2: Implement `database/mongodb/config.py`**

Load `.env` from `database/mongodb/` or root. Export `get_mongo_client()`, `get_mongo_db()`, and `get_mysql_engine()`.

- [ ] **Step 3: Verification test**

Run: `python -c "import sys; sys.path.insert(0, r'database/mongodb'); from config import get_mongo_db, get_mysql_engine; mdb = get_mongo_db(); eng = get_mysql_engine(); print('MongoDB:', mdb.name); print('MySQL:', eng)"`
Expected: prints `MongoDB: db_hr_mnc` and MySQL engine URL, exit code 0.

- [ ] **Step 4: Commit**

```bash
git add database/mongodb/config.py database/mongodb/.env.example
git commit -m "feat(mongodb): add configuration and client connection loaders"
```

---

### Task 2: Fast Streaming Loader from MySQL to MongoDB

**Files:**
- Create: `database/mongodb/load_mysql_to_mongodb.py`

**Interfaces:**
- Consumes: Task 1's `get_mongo_db`, `get_mysql_engine`.
- Produces: `load_employees(mysql_engine, mongo_db, chunk_size=50_000) -> int`, CLI `python load_mysql_to_mongodb.py`.

- [ ] **Step 1: Implement chunked streaming and indexing in `load_mysql_to_mongodb.py`**

1. If `mongo_db.employees.count_documents({}) == 2_000_000`, print message and skip load.
2. Stream `hr_employee` in slices of `chunk_size` (e.g. 50,000) using `WHERE row_id >= :start AND row_id < :end`.
3. Convert each row into a BSON document with `_id: employee_id`.
4. Call `collection.insert_many(docs, ordered=False)`.
5. After load completes, build secondary indexes on `department`, `job_title`, `status`, `work_mode`, `salary_inr`.

- [ ] **Step 2: Run verification test**

Run: `python database/mongodb/load_mysql_to_mongodb.py`
Expected: Output tracks progress up to 2,000,000 rows; indexes created; asserts 2,000,000 documents; exit code 0.

- [ ] **Step 3: Re-run idempotency test**

Run: `python database/mongodb/load_mysql_to_mongodb.py` again.
Expected: Detects existing 2,000,000 documents and skips load without error; exit code 0.

- [ ] **Step 4: Commit**

```bash
git add database/mongodb/load_mysql_to_mongodb.py
git commit -m "feat(mongodb): implement chunked streaming loader for 2M employee documents"
```

---

### Task 3: Aggregation Pipeline Generator for Summaries

**Files:**
- Create: `database/mongodb/generate_summaries.py`

**Interfaces:**
- Consumes: Task 1's `get_mongo_db`, Task 2's populated `employees` collection.
- Produces: `generate_all_summaries(mongo_db) -> dict[str, int]`, CLI `python generate_summaries.py`.

- [ ] **Step 1: Implement MongoDB Aggregation Pipelines in `generate_summaries.py`**

1. `generate_overview(db)`: `$group` on null computing total headcount, total payroll, min/max/avg salary, avg experience, avg rating, status distribution, and work mode distribution. Saves 1 doc to `hr_overview_summary` with `_id: "global"`.
2. `generate_departments(db)`: `$group` on `$department` computing employee_count, total payroll, avg/min/max salary, avg exp, avg rating. Saves 7 docs to `department_summary` with `_id: department`.
3. `generate_job_titles(db)`: `$group` on `$job_title` computing employee_count, department, avg/min/max salary, avg exp, avg rating. Saves 29 docs to `job_title_summary` with `_id: slugified job_title`.
4. `generate_work_modes(db)`: `$group` on `$work_mode` computing employee_count, share %, avg salary, avg rating. Saves 2 docs to `work_mode_summary` with `_id: slugified work_mode`.

- [ ] **Step 2: Run verification test**

Run: `python database/mongodb/generate_summaries.py`
Expected: Output prints 1 overview doc, 7 department docs, 29 job title docs, 2 work mode docs created; exit code 0.

- [ ] **Step 3: Commit**

```bash
git add database/mongodb/generate_summaries.py
git commit -m "feat(mongodb): generate summary collections via native aggregation pipelines"
```

---

### Task 4: Live Query Verifier

**Files:**
- Create: `database/mongodb/verify_mongodb.py`

**Interfaces:**
- Consumes: Task 1's `get_mongo_db`.
- Produces: CLI `python verify_mongodb.py` exiting 0 on PASS, 1 on FAIL.

- [ ] **Step 1: Implement verification checks in `verify_mongodb.py`**

1. Asserts document counts:
   - `employees`: 2,000,000
   - `department_summary`: 7
   - `job_title_summary`: 29
   - `work_mode_summary`: 2
   - `hr_overview_summary`: 1
2. Asserts business invariants: sum of department headcounts == 2,000,000.
3. Tests query performance: query `employees.find({"department": "IT"}).limit(5)` and measures latency (< 5ms).
4. Prints formatted summary table and outputs `FINAL RESULT: PASS`.

- [ ] **Step 2: Run verification**

Run: `python database/mongodb/verify_mongodb.py`
Expected: All 5 collections pass counts and fields, latency < 5ms, `FINAL RESULT: PASS`, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add database/mongodb/verify_mongodb.py
git commit -m "test(mongodb): add live verification script for MongoDB dataset and summaries"
```

---

### Task 5: Documentation & MongoDB Compass Guide

**Files:**
- Create: `database/mongodb/README.md`

- [ ] **Step 1: Write `database/mongodb/README.md`**

Document:
1. Role of MongoDB in the system (Full 2,000,000 Document Store vs MySQL Master & Firestore Cloud).
2. Collection structures and schemas.
3. Setup and execution steps (`pip install pymongo`, `load_mysql_to_mongodb.py`, `generate_summaries.py`, `verify_mongodb.py`).
4. Step-by-step guide to connect and view data in **MongoDB Compass** (`mongodb://localhost:27017/` -> `db_hr_mnc`).

- [ ] **Step 2: Commit**

```bash
git add database/mongodb/README.md
git commit -m "docs(mongodb): document full MongoDB NoSQL layer and Compass guide"
```
