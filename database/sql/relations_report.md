# Relations report — Normalized Schema

Generated: `2026-11-10T11:52:41.125316+00:00`
Database: `root@127.0.0.1:3306/db_hr_mnc`

Server version: **MySQL 8.0.30**

## Table inventory

| Table | Exact Rows | Data + Index Size (MB) |
|---|---:|---:|
| `dim_department` | 7 | 0.02 |
| `dim_job_title` | 29 | 0.02 |
| `dim_status` | 4 | 0.02 |
| `dim_work_mode` | 2 | 0.02 |
| `hr_employee` | 2,000,000 | 453.27 |

## hr_employee Schema Structure

| Ordinal | Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|---|
| 1 | `row_id` | `int unsigned` | NO | PRI | None |  |
| 2 | `employee_id` | `char(10)` | NO | UNI | None |  |
| 3 | `full_name` | `varchar(64)` | NO |  | None |  |
| 4 | `department` | `varchar(10)` | NO | MUL | None |  |
| 5 | `job_title` | `varchar(29)` | NO | MUL | None |  |
| 6 | `hire_date` | `date` | NO | MUL | None |  |
| 7 | `location` | `varchar(120)` | NO |  | None |  |
| 8 | `performance_rating` | `tinyint unsigned` | NO |  | None |  |
| 9 | `experience_years` | `tinyint unsigned` | NO |  | None |  |
| 10 | `status` | `varchar(10)` | NO | MUL | None |  |
| 11 | `work_mode` | `varchar(7)` | NO | MUL | None |  |
| 12 | `salary_inr` | `int unsigned` | NO |  | None |  |

## Foreign Keys

| Constraint | Child Column | Parent Table | Parent Column | On Update | On Delete |
|---|---|---|---|---|---|
| `fk_employee_department` | `hr_employee.department` | `dim_department` | `department` | NO ACTION | NO ACTION |
| `fk_employee_job_title` | `hr_employee.job_title` | `dim_job_title` | `job_title` | NO ACTION | NO ACTION |
| `fk_employee_status` | `hr_employee.status` | `dim_status` | `status` | NO ACTION | NO ACTION |
| `fk_employee_work_mode` | `hr_employee.work_mode` | `dim_work_mode` | `work_mode` | NO ACTION | NO ACTION |

## Foreign Key Orphan Checks

| Child Column | Referenced Dimension | Orphan Rows | Status |
|---|---|---:|---|
| `hr_employee.department` | `dim_department.department` | 0 | PASS |
| `hr_employee.job_title` | `dim_job_title.job_title` | 0 | PASS |
| `hr_employee.status` | `dim_status.status` | 0 | PASS |
| `hr_employee.work_mode` | `dim_work_mode.work_mode` | 0 | PASS |

## Null Checks (hr_employee)

| Column | Null Count | Status |
|---|---:|---|
| `row_id` | 0 | PASS |
| `employee_id` | 0 | PASS |
| `full_name` | 0 | PASS |
| `department` | 0 | PASS |
| `job_title` | 0 | PASS |
| `hire_date` | 0 | PASS |
| `location` | 0 | PASS |
| `performance_rating` | 0 | PASS |
| `experience_years` | 0 | PASS |
| `status` | 0 | PASS |
| `work_mode` | 0 | PASS |
| `salary_inr` | 0 | PASS |

## Sample Data (5 rows)

| row_id | employee_id | full_name | department | job_title | hire_date | location | performance_rating | experience_years | status | work_mode | salary_inr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | EMP0000001 | Joshua Nguyen | IT | Software Engineer | 2011-08-10 | Isaacland, Denmark | 5 | 14 | Resigned | On-site | 1585363 |
| 1 | EMP0000002 | Julie Williams | Marketing | SEO Specialist | 2018-03-02 | Anthonyside, Costa Rica | 2 | 7 | Active | On-site | 847686 |
| 2 | EMP0000003 | Alyssa Martinez | HR | HR Manager | 2023-03-20 | Port Christinaport, Saudi Arabia | 1 | 2 | Active | On-site | 1430084 |
| 3 | EMP0000004 | Nicholas Valdez | IT | Software Engineer | 2023-10-12 | Port Shelbychester, Antigua and Barbuda | 1 | 1 | Active | On-site | 990689 |
| 4 | EMP0000005 | Joel Hendricks | Operations | Logistics Coordinator | 2024-12-09 | Lake Kimberly, Palestinian Territory | 5 | 0 | Active | On-site | 535082 |

## Final Result: PASS
