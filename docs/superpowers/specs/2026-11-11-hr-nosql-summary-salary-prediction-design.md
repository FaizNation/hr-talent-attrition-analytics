# HR Dataset NoSQL Summary Layer Design (Cloud Firestore)

Date: 2026-11-11
Status: approved (focused exclusively on NoSQL summary layer)

## Intent

Implement a direct **MySQL-to-NoSQL Conversion & Summary Layer** using **Cloud Firestore (`hr-mnc-database`)**, consuming the 2,000,000 normalized employee records from MySQL (`db_hr_mnc`).

Fulfills the core course requirements:
- **MySQL (`db_hr_mnc`)**: Single source of truth / System of Record (raw 2,000,000 rows in 3NF normalized tables).
- **NoSQL (`hr-mnc-database`)**: Directly converted and pre-aggregated summaries of the HR dataset for instant query consumption.
- **Zero non-HR artifacts**: No external startup benchmarks or foreign data; 100% derived from the HR dataset.

---

## Collections & Document Schemas

All documents are extracted directly from MySQL table `hr_employee` and its dimensions:

### 1. `hr_overview_summary` (1 document: `global`)
Organizational macro metrics across the 2,000,000 employees:
```json
{
  "total_employees": 2000000,
  "total_payroll_inr": 3662580000000,
  "avg_salary_inr": 1831290.0,
  "min_salary_inr": 300000,
  "max_salary_inr": 2999976,
  "avg_experience_years": 7.5,
  "avg_performance_rating": 3.0,
  "status_distribution": {
    "Active": 1400000,
    "Resigned": 400000,
    "Terminated": 100000,
    "On Leave": 100000
  },
  "work_mode_distribution": {
    "On-site": 1000500,
    "Remote": 999500
  },
  "updated_at": "TIMESTAMP"
}
```

### 2. `department_summary` (7 documents)
Document ID: department name (`IT`, `Finance`, `Sales`, `HR`, `Marketing`, `R&D`, `Operations`)
```json
{
  "department": "IT",
  "employee_count": 285400,
  "headcount_percentage": 14.27,
  "total_payroll_inr": 523000000000,
  "avg_salary_inr": 1832000.0,
  "min_salary_inr": 300000,
  "max_salary_inr": 2999976,
  "avg_experience_years": 7.5,
  "avg_performance_rating": 3.01,
  "updated_at": "TIMESTAMP"
}
```

### 3. `job_title_summary` (29 documents)
Document ID: slugified job title (e.g., `software_engineer`, `data_analyst`)
```json
{
  "job_title": "Software Engineer",
  "department": "IT",
  "employee_count": 300358,
  "avg_salary_inr": 1835000.0,
  "min_salary_inr": 300000,
  "max_salary_inr": 2999500,
  "avg_experience_years": 7.5,
  "avg_performance_rating": 3.0,
  "updated_at": "TIMESTAMP"
}
```

### 4. `work_mode_summary` (2 documents: `on_site`, `remote`)
```json
{
  "work_mode": "On-site",
  "employee_count": 1000500,
  "share_percentage": 50.02,
  "avg_salary_inr": 1830000.0,
  "avg_performance_rating": 3.0,
  "updated_at": "TIMESTAMP"
}
```

### 5. `employee_sample` (500 documents)
Document ID: `employee_id` (e.g. `EMP0000001`)
Demonstrates denormalized employee document storage directly from MySQL:
```json
{
  "employee_id": "EMP0000001",
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
*(Privacy: `full_name` is excluded).*

---

## Cleanup of Stale Collections
During upload, any non-HR legacy collections (`startup_stage_presets`, `department_benchmarks`, `role_benchmarks`, `work_mode_profiles`) created in earlier experiments are safely purged from Firestore.

---

## Architecture & Directory Layout (`database/firestore/`)

1. `config.py`: Firestore Admin SDK & MySQL connection loader.
2. `extract_from_mysql.py`: Aggregates the 2M records into the 4 summary tables + 500 denormalized employee samples.
3. `upload_to_firestore.py`: Atomic batched writes uploading the 4 summary collections + sample documents.
4. `verify_firestore.py`: Automated query verifier asserting document counts and fields.
5. `README.md`: Clear documentation of the MySQL-to-NoSQL summary pipeline.
