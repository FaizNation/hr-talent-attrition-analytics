# MongoDB Full Dataset & Summary Layer Design

Date: 2026-11-11
Status: proposed (awaiting user approval)

## Intent

Implement a complete, high-volume local **NoSQL Layer using MongoDB 8.2**, complementing the Cloud Firestore summary layer.
While Cloud Firestore serves as the quota-safe cloud demo (summaries + 500 samples), MongoDB serves as the **Full-Scale 2,000,000 Document Store & Aggregation Engine**.

Fulfills the core course requirements:
1. **Full 2,000,000 Raw Document Conversion:** Directly copies all 2,000,000 records from MySQL `hr_employee` into MongoDB collection `employees`.
2. **MongoDB Aggregation Pipelines (Summaries):** Generates analytical summary collections directly via MongoDB `$group` and `$facet` pipelines:
   - `hr_overview_summary` (1 doc)
   - `department_summary` (7 docs)
   - `job_title_summary` (29 docs)
   - `work_mode_summary` (2 docs)
3. **High Performance & Zero Cloud Limits:** Operates locally on MongoDB 8.2 (port 27017) with zero daily write quotas and sub-millisecond query lookups.

---

## 1. MongoDB Database & Collections (`db_hr_mnc`)

### Database: `db_hr_mnc`

### Primary Collection: `employees` (2,000,000 documents)
Document ID: `_id` = `employee_id` (e.g. `"EMP0000001"`)
```json
{
  "_id": "EMP0000001",
  "row_id": 0,
  "employee_id": "EMP0000001",
  "full_name": "John Doe",
  "department": "IT",
  "job_title": "Software Engineer",
  "hire_date": "2020-05-15",
  "location": "Bangalore, India",
  "performance_rating": 4,
  "experience_years": 6,
  "status": "Active",
  "work_mode": "Remote",
  "salary_inr": 1850000
}
```
Indexes:
- `department`: 1
- `job_title`: 1
- `status`: 1
- `work_mode`: 1
- `salary_inr`: 1

### Summary Collections (Generated via MongoDB Aggregation Pipelines):
1. **`hr_overview_summary`** (1 document: `_id`: `"global"`)
   - `total_employees`: 2,000,000
   - `total_payroll_inr`: sum of all salaries
   - `avg_salary_inr`, `min_salary_inr`, `max_salary_inr`
   - `avg_experience_years`, `avg_performance_rating`
   - `status_distribution`: `{ "Active": 1400000, ... }`
   - `work_mode_distribution`: `{ "On-site": 1000500, "Remote": 999500 }`

2. **`department_summary`** (7 documents: `_id`: department name)
   - `department`: string
   - `employee_count`: int
   - `headcount_percentage`: float
   - `total_payroll_inr`: int
   - `avg_salary_inr`, `min_salary_inr`, `max_salary_inr`
   - `avg_experience_years`, `avg_performance_rating`

3. **`job_title_summary`** (29 documents: `_id`: slugified job title)
   - `job_title`: string
   - `department`: string
   - `employee_count`: int
   - `avg_salary_inr`, `min_salary_inr`, `max_salary_inr`
   - `avg_experience_years`, `avg_performance_rating`

4. **`work_mode_summary`** (2 documents: `_id`: `on_site` / `remote`)
   - `work_mode`: string
   - `employee_count`: int
   - `share_percentage`: float
   - `avg_salary_inr`, `avg_performance_rating`

---

## 2. Architecture & File Structure (`database/mongodb/`)

1. `config.py`: MongoDB connection URL (`mongodb://localhost:27017/`), database name (`db_hr_mnc`), and MySQL connection settings loaded via `.env`.
2. `load_mysql_to_mongodb.py`: Fast chunked streaming from MySQL `hr_employee` in batches of 50,000 rows using `insert_many(..., ordered=False)`. Idempotent resume support. Creates secondary indexes.
3. `generate_summaries.py`: Runs MongoDB native aggregation pipelines (`$group`, `$project`, `$out` / `$merge`) to populate the summary collections directly in MongoDB.
4. `verify_mongodb.py`: Automated verification testing document counts (2M employees, 7 depts, 29 roles, 2 work modes, 1 overview), index presence, and sample query performance.
5. `README.md`: Comprehensive documentation with MongoDB Compass viewing instructions and execution guide.
