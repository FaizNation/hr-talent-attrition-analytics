# HR Dataset NoSQL Summary Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the Firestore NoSQL layer into a pure, direct MySQL-to-NoSQL summary and document conversion layer for the 2,000,000-row HR MNC dataset.

**Architecture:** Polyglot persistence. MySQL (`db_hr_mnc`) serves as the 3NF relational master (System of Record). Python ETL pipeline queries and aggregates the relational master, then uploads 4 aggregate summary collections plus 500 denormalized employee sample records into Cloud Firestore (`hr-mnc-database`), purging any non-HR legacy collections.

**Tech Stack:** Python 3.10, `firebase-admin`, `google-cloud-firestore`, SQLAlchemy, PyMySQL, MySQL 8.0.

**Spec:** `docs/superpowers/specs/2026-11-11-hr-nosql-summary-salary-prediction-design.md`

## Global Constraints

- Zero non-HR artifacts: no external startup datasets, burn rates, or foreign benchmarks.
- Privacy boundary: `full_name` is never uploaded to Firestore; `employee_sample` uses `employee_id` only.
- Target collections:
  - `hr_overview_summary` (1 doc: `global`)
  - `department_summary` (7 docs)
  - `job_title_summary` (29 docs)
  - `work_mode_summary` (2 docs)
  - `employee_sample` (500 docs)
- All numbers must be native Python primitives (`int`, `float`, `str`, `dict`, `list`), no `Decimal` or `NaN`.

## Review Focus

- Decimals in MySQL aggregate results: must be converted to float/int to prevent Firestore serialization errors.
- Batch write limits: Firestore allows maximum 500 operations per batch; the 539 total documents (1 + 7 + 29 + 2 + 500) must be batched in chunks <= 500.
- Legacy collection leakage: old collections (`startup_stage_presets`, `department_benchmarks`, `role_benchmarks`, `work_mode_profiles`) must be completely purged from Firestore.
- Data integrity: sum of department headcounts in `department_summary` and in `hr_overview_summary` must strictly equal 2,000,000.
- Re-run safety: running the ETL pipeline multiple times must cleanly overwrite without duplicate documents.

---

### Task 1: Rewrite Extractor (`extract_from_mysql.py`)

**Files:**
- Modify: `database/firestore/extract_from_mysql.py`

**Interfaces:**
- Produces: `extract_all(engine: Engine) -> dict[str, list[dict]]` with keys `"overview"`, `"departments"`, `"job_titles"`, `"work_modes"`, `"employee_sample"`.

- [ ] **Step 1: Implement 5 extraction queries in `extract_from_mysql.py`**

1. `extract_overview(engine)`: single row aggregate computing total headcount (2,000,000), total payroll, avg salary, min/max salary, avg experience, avg rating, status breakdown dict (`Active`, `Resigned`, `Terminated`, `On Leave`), and work mode breakdown.
2. `extract_departments(engine)`: 7 rows from `dim_department` + `hr_employee`.
3. `extract_job_titles(engine)`: 29 rows from `dim_job_title` + `hr_employee`.
4. `extract_work_modes(engine)`: 2 rows from `dim_work_mode` + `hr_employee`.
5. `extract_employee_sample(engine, limit=500)`: 500 denormalized records from `hr_employee` omitting `full_name`.

- [ ] **Step 2: Run verification test**

Run: `python database/firestore/extract_from_mysql.py`
Expected: Output prints 1 overview, 7 departments, 29 job titles, 2 work modes, 500 employee samples; total headcount = 2,000,000; exit 0.

- [ ] **Step 3: Commit**

```bash
git add database/firestore/extract_from_mysql.py
git commit -m "refactor(firestore): extract pure HR summaries and employee samples from MySQL"
```

---

### Task 2: Rewrite Uploader with Purge & Batch Chunks (`upload_to_firestore.py`)

**Files:**
- Modify: `database/firestore/upload_to_firestore.py`

**Interfaces:**
- Consumes: Task 1's `extract_all`.
- Produces: `upload_all(db, data: dict) -> dict[str, int]`, CLI `python upload_to_firestore.py`.

- [ ] **Step 1: Implement collection purger and chunked batch uploader in `upload_to_firestore.py`**

1. `purge_legacy_collections(db)`: deletes documents in old collections (`startup_stage_presets`, `department_benchmarks`, `role_benchmarks`, `work_mode_profiles`).
2. `commit_in_batches(db, operations, batch_size=450)`: splits operations into batches under the 500 Firestore limit.
3. Upload target collections: `hr_overview_summary`, `department_summary`, `job_title_summary`, `work_mode_summary`, `employee_sample`.

- [ ] **Step 2: Run verification test**

Run: `python database/firestore/upload_to_firestore.py`
Expected: Legacy collections purged; 539 documents uploaded across 5 collections; exit 0.

- [ ] **Step 3: Commit**

```bash
git add database/firestore/upload_to_firestore.py
git commit -m "refactor(firestore): upload HR summaries and employee samples with chunked batching"
```

---

### Task 3: Rewrite Live Verifier (`verify_firestore.py`)

**Files:**
- Modify: `database/firestore/verify_firestore.py`

**Interfaces:**
- Produces: CLI `python verify_firestore.py` exiting 0 on PASS, 1 on FAIL.

- [ ] **Step 1: Implement verification assertions in `verify_firestore.py`**

Assert:
- `hr_overview_summary`: 1 doc (`global`), total_employees = 2,000,000.
- `department_summary`: 7 docs, sum of employee_count = 2,000,000.
- `job_title_summary`: 29 docs.
- `work_mode_summary`: 2 docs (`on_site`, `remote`).
- `employee_sample`: 500 docs, zero `full_name` fields.
- Stale collections (`startup_stage_presets`, etc.) contain 0 documents.

- [ ] **Step 2: Run verification**

Run: `python database/firestore/verify_firestore.py`
Expected: All 5 collections verified, legacy collections verified 0 docs, `FINAL RESULT: PASS`, exit 0.

- [ ] **Step 3: Commit**

```bash
git add database/firestore/verify_firestore.py
git commit -m "test(firestore): verify HR summary collections and sample documents"
```

---

### Task 4: Documentation Update (`README.md`)

**Files:**
- Modify: `database/firestore/README.md`

- [ ] **Step 1: Rewrite `database/firestore/README.md`**

Document the 5 HR collections, MySQL source mapping, privacy rules, setup and execution workflow.

- [ ] **Step 2: Commit**

```bash
git add database/firestore/README.md
git commit -m "docs(firestore): document pure HR NoSQL summary layer"
```
