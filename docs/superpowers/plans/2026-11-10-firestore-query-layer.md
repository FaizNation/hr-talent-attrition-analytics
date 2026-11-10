# Firestore Read-Optimized Query Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Cloud Firestore read-optimized NoSQL serving layer for the HR Workforce Cost & Startup Runway Simulator, consuming aggregated metrics from the 2,000,000-row MySQL master database.

**Architecture:** Polyglot persistence. MySQL (`db_hr_mnc`) acts as the single source of truth (System of Record). An ETL pipeline extracts pre-aggregated, denormalized payloads (`department_benchmarks`, `role_benchmarks`, `work_mode_profiles`, `startup_stage_presets`) and loads them into Google Cloud Firestore (`hr-mnc-database`) via batched writes for fast O(1) reads by dashboard clients.

**Tech Stack:** Python 3.10, `firebase-admin` 7.7.0, `google-cloud-firestore`, SQLAlchemy, PyMySQL, MySQL 8.0.

**Spec:** `docs/superpowers/specs/2026-11-10-firestore-query-layer-design.md`

## Global Constraints

- No personal identifiability: `full_name` and individual `employee_id` are never uploaded to Firestore.
- Credentials (`FIREBASE_CREDENTIALS_PATH`, database passwords) are loaded via `.env` only; no secrets committed to Git.
- Idempotent uploads: running `upload_to_firestore.py` repeatedly must overwrite existing documents cleanly with `set()` without creating duplicates.
- All numeric values must be standard Python primitives (`int`, `float`, `str`, `dict`, `list`) without `Decimal`, `numpy.int64`, or `NaN`.
- Four target collections: `department_benchmarks` (7 docs), `role_benchmarks` (29 docs), `work_mode_profiles` (2 docs), `startup_stage_presets` (3 docs).

## Review Focus

- Invalid or missing Firebase credentials path: `config.py` must raise a clear `FileNotFoundError` or `ValueError` rather than failing cryptically deep in the SDK.
- Decimals in payload: Firestore SDK fails on Python `decimal.Decimal`; extraction must convert all currency and ratios to native `float` / `int`.
- Offline or down MySQL during extract: extractor must fail early with a clear connection message and non-zero exit code.
- Incomplete collections: `verify_firestore.py` must assert exact document counts and key fields, failing if any document is missing.
- Re-run safety: executing the pipeline multiple times must not alter document IDs or cause transaction conflicts.

---

### Task 1: Package Scaffolding & Configuration

**Files:**
- Create: `database/firestore/config.py`
- Create: `database/firestore/.env.example`

**Interfaces:**
- Produces: `get_mysql_engine() -> Engine`, `get_firestore_client() -> firestore.Client`, constants `FIRESTORE_DIR`, `PROJECT_ROOT`.

- [ ] **Step 1: Create `database/firestore/.env.example`**

Include standard variables: `FIREBASE_CREDENTIALS_PATH`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.

- [ ] **Step 2: Implement `database/firestore/config.py`**

Resolve `.env` from `database/firestore/` or project root. Initialize `firebase_admin.initialize_app` with certificate and export `get_firestore_client()` and `get_mysql_engine()`.

- [ ] **Step 3: Verification test**

Run: `python -c "import sys; sys.path.insert(0, r'database/firestore'); from config import get_firestore_client, get_mysql_engine; db = get_firestore_client(); eng = get_mysql_engine(); print('Firestore project:', db.project); print('MySQL engine:', eng)"`
Expected: prints `Firestore project: hr-mnc-database` and MySQL engine URL, exit code 0.

- [ ] **Step 4: Commit**

```bash
git add database/firestore/config.py database/firestore/.env.example
git commit -m "feat(firestore): add configuration and client loaders"
```

---

### Task 2: Extraction Module from MySQL

**Files:**
- Create: `database/firestore/extract_from_mysql.py`

**Interfaces:**
- Consumes: Task 1's `get_mysql_engine`.
- Produces: `extract_all(engine: Engine) -> dict[str, list[dict]]` returning keys `"departments"`, `"roles"`, `"work_modes"`, `"presets"`.

- [ ] **Step 1: Implement aggregated SQL queries in `extract_from_mysql.py`**

1. `extract_departments(engine)`: Queries `dim_department` + `hr_employee`. Calculates headcount, percentage, avg salary, min, max, and maps `cost_category`. Returns 7 dicts.
2. `extract_roles(engine)`: Queries `dim_job_title` + `hr_employee`. Calculates median (using subquery or sorted array), min, max, avg salary, avg experience, avg performance. Returns 29 dicts.
3. `extract_work_modes(engine)`: Queries `dim_work_mode` + `hr_employee`. Calculates headcount, share %, avg salary, and assigns overhead factor (1.20 On-site, 1.03 Remote). Returns 2 dicts.
4. `extract_presets()`: Defines baseline financial parameters for `Seed`, `Series_A`, `Series_B`. Returns 3 dicts.
5. All floats rounded cleanly, zero Decimals.

- [ ] **Step 2: Verification test**

Run: `python database/firestore/extract_from_mysql.py`
Expected: Prints summary: 7 departments, 29 roles, 2 work modes, 3 presets. Total headcount verified as 2,000,000. Exit code 0.

- [ ] **Step 3: Commit**

```bash
git add database/firestore/extract_from_mysql.py
git commit -m "feat(firestore): implement MySQL aggregation extractor for runway metrics"
```

---

### Task 3: Batched Uploader to Firestore

**Files:**
- Create: `database/firestore/upload_to_firestore.py`

**Interfaces:**
- Consumes: Task 1's `get_firestore_client`, Task 2's `extract_all`.
- Produces: `upload_all(db, data: dict) -> dict[str, int]`, CLI `python upload_to_firestore.py`.

- [ ] **Step 1: Implement `upload_to_firestore.py`**

Use Firestore `batch = db.batch()`.
- Collection `department_benchmarks`: doc ID = department name (`IT`, `Finance`, etc.).
- Collection `role_benchmarks`: doc ID = slugified `job_title` (e.g. `software_engineer`).
- Collection `work_mode_profiles`: doc ID = `work_mode` (`On-site`, `Remote`).
- Collection `startup_stage_presets`: doc ID = `stage` (`Seed`, `Series_A`, `Series_B`).
Call `batch.commit()`.

- [ ] **Step 2: Verification test**

Run: `python database/firestore/upload_to_firestore.py`
Expected: Prints `Uploaded 7 departments`, `Uploaded 29 roles`, `Uploaded 2 work modes`, `Uploaded 3 presets`, `Batch commit successful`. Exit code 0.

- [ ] **Step 3: Re-run idempotency test**

Run `python database/firestore/upload_to_firestore.py` a second time immediately.
Expected: Overwrites without errors or duplicate documents. Exit code 0.

- [ ] **Step 4: Commit**

```bash
git add database/firestore/upload_to_firestore.py
git commit -m "feat(firestore): implement batched uploader for runway collections"
```

---

### Task 4: Live Query Verifier

**Files:**
- Create: `database/firestore/verify_firestore.py`

**Interfaces:**
- Consumes: Task 1's `get_firestore_client`.
- Produces: CLI `python verify_firestore.py` exiting 0 on PASS, 1 on FAIL.

- [ ] **Step 1: Implement `verify_firestore.py`**

For each collection, query all documents from Firestore:
- `department_benchmarks`: asserts 7 documents, checks required keys (`avg_salary_inr`, `employee_count`, `cost_category`).
- `role_benchmarks`: asserts 29 documents, checks required keys (`market_median_salary_inr`, `department`).
- `work_mode_profiles`: asserts 2 documents, checks required keys (`overhead_factor`).
- `startup_stage_presets`: asserts 3 documents, checks required keys (`initial_cash_balance_inr`, `rd_spend_ratio`).
Prints formatted check table and outputs `RESULT: PASS`.

- [ ] **Step 2: Run verification**

Run: `python database/firestore/verify_firestore.py`
Expected: 4 collections verified, all document counts matched, `RESULT: PASS`, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add database/firestore/verify_firestore.py
git commit -m "feat(firestore): add live query verification script"
```

---

### Task 5: Documentation & Clean-up

**Files:**
- Create: `database/firestore/README.md`
- Update: `README.md` (root, if appropriate)

**Interfaces:**
- Produces: Complete architectural guide explaining Polyglot Persistence, document schemas, and execution commands.

- [ ] **Step 1: Write `database/firestore/README.md`**

Document:
1. Role of Firestore in the system (Read-Optimized Serving Layer vs MySQL Master).
2. Collection dictionaries and schema fields.
3. Setup and execution steps (`pip install`, `.env` setup, `extract_from_mysql.py`, `upload_to_firestore.py`, `verify_firestore.py`).
4. Security and privacy rules (read-only for clients, no PII uploaded).

- [ ] **Step 2: Verify git status and clean tree**

Run: `git status`
Confirm no stray or temporary files untracked in `database/firestore`.

- [ ] **Step 3: Commit**

```bash
git add database/firestore/README.md
git commit -m "docs(firestore): document NoSQL serving layer architecture and pipeline"
```
