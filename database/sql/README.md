# HR Analytics — Normalized SQL Database Layer

This directory manages the relational database layer (`db_hr_mnc`) for the
**Workforce Cost & Startup Runway Simulator** project.

The SQL database is strictly scoped to store the **12 raw dataset columns**
from the Kaggle MNC HR dataset in a normalized 3NF structure.

---

## 1. Schema & Entity-Relationship Design

The schema separates categorical attributes into 4 natural-key dimension tables
enforced by strict foreign key constraints on the central fact table:

```
+--------------------+        +--------------------+
|   dim_department   |        |   dim_job_title    |
+--------------------+        +--------------------+
| department (PK)    |<---+   | job_title (PK)     |<---+
+--------------------+    |   +--------------------+    |
                          |                             |
+--------------------+    |   +--------------------+    |
|     dim_status     |    |   |   dim_work_mode    |    |
+--------------------+    |   +--------------------+    |
| status (PK)        |<-+ |   | work_mode (PK)     |<-+ |
+--------------------+  | |   +--------------------+  | |
                        | |                           | |
              +---------|-|---------------------------|-|+
              |         | |     hr_employee           | |
              +---------|-|---------------------------|-|+
              | row_id             INT UNSIGNED (PK)  | |
              | employee_id        CHAR(10) (UQ)      | |
              | full_name          VARCHAR(64)        | |
              | department         VARCHAR(10) (FK)---+ |
              | job_title          VARCHAR(29) (FK)-----+
              | hire_date          DATE (IDX)         | |
              | location           VARCHAR(120)       | |
              | performance_rating TINYINT UNSIGNED   | |
              | experience_years   TINYINT UNSIGNED   | |
              | status             VARCHAR(10) (FK)---+ |
              | work_mode          VARCHAR(7)  (FK)-----+
              | salary_inr         INT UNSIGNED       |
              +---------------------------------------+
```

### Key Architectural Decisions

1. **Strict Raw Boundary:** SQL holds only the 12 original Kaggle dataset columns. No derived metrics (SDI, tenure, cost, archetype, attrition scores) are stored in MySQL. All feature engineering and simulation modeling live strictly in `Startup_Runway_Workforce_Simulator_KDD.ipynb` (proposal Tabel 3.2).
2. **Location is not normalized:** In the 2,000,000 rows, `Location` contains **1,593,497 distinct values** (~80% uniqueness). Creating a `dim_location` table would duplicate storage and penalize join performance with zero analytical gain. `Location` remains a single raw column (`VARCHAR(120)`) and is never split into synthetic city/country columns.
3. **Natural Keys for Dimensions:** Dimensions use their natural string values as primary keys (`VARCHAR`), matching production dimensions and eliminating lookup joins for simple filters.
4. **Data Integrity:** Inline foreign keys (`ON UPDATE RESTRICT`, `ON DELETE RESTRICT`) ensure referential integrity with zero orphan records.

---

## 2. Table Inventory & Expected Row Counts

| Table | Role | Expected Rows | Primary Key |
|---|---|---:|---|
| `hr_employee` | Fact table (raw records) | 2,000,000 | `row_id` (`INT UNSIGNED`) |
| `dim_department` | Dimension | 7 | `department` (`VARCHAR(10)`) |
| `dim_job_title` | Dimension | 29 | `job_title` (`VARCHAR(29)`) |
| `dim_status` | Dimension | 4 | `status` (`VARCHAR(10)`) |
| `dim_work_mode` | Dimension | 2 | `work_mode` (`VARCHAR(7)`) |

---

## 3. Setup & Prerequisites

- Python 3.10+
- MySQL 8.0+ running on port 3306 (InnoDB engine, `utf8mb4_0900_ai_ci`)
- Database `db_hr_mnc`

Install Python dependencies:

```bash
python -m pip install SQLAlchemy PyMySQL pandas python-dotenv
```

Configure credentials in `.env` (copied from `.env.example`):

```bash
cd database/sql
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/macOS
```

Edit `.env` with your MySQL connection credentials:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=db_hr_mnc
```

*(Note: `.env` is git-ignored; never commit passwords).*

---

## 4. Execution Workflow

All scripts are idempotent and run from `database/sql/`:

### Step 1: Create Schema & Populate Dimensions
```bash
python create_schema.py --phase base
```
Creates the 4 dimension tables and `hr_employee` with inline foreign keys and indexes. Populates the 4 dimension tables with distinct values.

### Step 2: Load Data
```bash
python load_data.py
```
Performs an idempotent, chunked set-based copy from `hr_attrition` into `hr_employee` in 100,000-row batches. Validates pre-flight invariants (valid dates, location lengths, dimension completeness) and verifies the 2,000,000 final row count.

### Step 3: Verify Integrity & Generate Relations Report
```bash
python inspect_db.py
```
Runs comprehensive live verification (FK integrity, orphan checks, null checks, table sizes) and writes `relations_report.md`. Exits with code 1 if any check fails.

### Step 4: Run Reporting Queries
```bash
python queries.py
```
Executes four analytical queries and writes structured JSON files to `output/`:
- `q1_headcount_by_department.json`: Department headcount, share %, and average salary.
- `q2_salary_by_job_title.json`: Salary bounds (min, avg, max) and headcount per job title.
- `q3_work_mode_split.json`: Headcount and salary breakdown by work mode.
- `q4_hire_cohort.json`: Hiring cohort distribution per year (2010–2025).

### Step 5: Capture Query Execution Plans
```bash
python create_schema.py --phase explain
```
Generates EXPLAIN query plans for reporting queries into `output/explain_after.json`.

### Step 6: Drop Retired Legacy Tables (Post-Verification Guard)
```bash
python create_schema.py --drop-legacy --yes
```
Safely drops old-title tables (`hr_features`, `branch_efficiency`, `hr_attrition`, `dim_country`, `dim_talent_segment`). Protected by an assert requiring `hr_employee` to hold exactly 2,000,000 verified rows before proceeding.
