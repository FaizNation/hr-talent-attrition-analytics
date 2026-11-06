# Relations report

Generated: `2026-11-06T11:08:48.329236+00:00`

## Before

- Foreign keys present: **9**
- The brief described 5 FKs; any additional ones were added by the earlier `create_schema.py --phase indexes` run and are listed below.

| child.column | parent.column | constraint | ON UPDATE | ON DELETE |
|---|---|---|---|---|
| branch_efficiency.country | dim_country.country | `fk_branch_country` | NO ACTION | NO ACTION |
| branch_efficiency.department | dim_department.department | `fk_branch_department` | NO ACTION | NO ACTION |
| branch_efficiency.work_mode | dim_work_mode.work_mode | `fk_branch_work_mode` | NO ACTION | NO ACTION |
| hr_features.country | dim_country.country | `fk_hf_country` | NO ACTION | NO ACTION |
| hr_features.department | dim_department.department | `fk_hf_department` | NO ACTION | NO ACTION |
| hr_features.job_title | dim_job_title.job_title | `fk_hf_job_title` | NO ACTION | NO ACTION |
| hr_features.status | dim_status.status | `fk_hf_status` | NO ACTION | NO ACTION |
| hr_features.talent_segment | dim_talent_segment.talent_segment | `fk_hf_talent_segment` | NO ACTION | NO ACTION |
| hr_features.work_mode | dim_work_mode.work_mode | `fk_hf_work_mode` | NO ACTION | NO ACTION |

## Row counts

| table | rows |
|---|---:|
| branch_efficiency | 3,402 |
| dim_country | 243 |
| dim_department | 7 |
| dim_job_title | 29 |
| dim_status | 4 |
| dim_talent_segment | 4 |
| dim_work_mode | 2 |
| hr_attrition | 2,000,000 |
| hr_features | 2,000,000 |

- `hr_features` = **2,000,000**, `hr_attrition` = **2,000,000** → 1 : 1

## Column compatibility

| FK | child type | parent type | status |
|---|---|---|---|
| `fk_hf_job_title` | `varchar(29)` (utf8mb4_0900_ai_ci) | `varchar(29)` (utf8mb4_0900_ai_ci) | OK |
| `fk_hf_status` | `varchar(10)` (utf8mb4_0900_ai_ci) | `varchar(10)` (utf8mb4_0900_ai_ci) | OK |
| `fk_hf_work_mode` | `varchar(7)` (utf8mb4_0900_ai_ci) | `varchar(7)` (utf8mb4_0900_ai_ci) | OK |
| `fk_hf_talent_segment` | `varchar(33)` (utf8mb4_0900_ai_ci) | `varchar(33)` (utf8mb4_0900_ai_ci) | OK |
| `fk_hf_attrition` | `char(10)` (utf8mb4_0900_ai_ci) | `varchar(255)` (utf8mb4_0900_ai_ci) | SOFT-WARN |

## Orphan checks (Step 2)

| FK | child.column | parent.column | orphan rows | sample values |
|---|---|---|---:|---|
| `fk_hf_job_title` | `hr_features.job_title` | `dim_job_title.job_title` | 0 | - |
| `fk_hf_status` | `hr_features.status` | `dim_status.status` | 0 | - |
| `fk_hf_work_mode` | `hr_features.work_mode` | `dim_work_mode.work_mode` | 0 | - |
| `fk_hf_talent_segment` | `hr_features.talent_segment` | `dim_talent_segment.talent_segment` | 0 | - |
| `fk_hf_attrition` | `hr_features.employee_id` | `hr_attrition.employee_id` | 0 | - |

### hr_attrition.employee_id health

- total: 2,000,000
- non-null: 2,000,000
- nulls: 0
- duplicates: 0
- distinct: 2,000,000

## Dimension quality checks

| dim | rows | dim whitespace | fact whitespace | case mismatch | samples |
|---|---:|---:|---:|---:|---|
| `dim_country` | 243 | 0 | 0 | 0 | - |
| `dim_department` | 7 | 0 | 0 | 0 | - |
| `dim_job_title` | 29 | 0 | 0 | 0 | - |
| `dim_work_mode` | 2 | 0 | 0 | 0 | - |
| `dim_status` | 4 | 0 | 0 | 0 | - |
| `dim_talent_segment` | 4 | 0 | 0 | 0 | - |

## Fixes (Step 3)

No fixes were needed.

## Foreign keys added (Step 4)

| constraint | status | elapsed |
|---|---|---:|
| `fk_hf_job_title` | ALREADY EXISTS | 0.0s |
| `fk_hf_status` | ALREADY EXISTS | 0.0s |
| `fk_hf_work_mode` | ALREADY EXISTS | 0.0s |
| `fk_hf_talent_segment` | ALREADY EXISTS | 0.0s |
| `fk_hf_attrition` | ADDED | 315.8s |

## After (Step 5)

- Foreign keys present: **10** (expected 10)

| child.column | parent.column | constraint |
|---|---|---|
| branch_efficiency.country | dim_country.country | `fk_branch_country` |
| branch_efficiency.department | dim_department.department | `fk_branch_department` |
| branch_efficiency.work_mode | dim_work_mode.work_mode | `fk_branch_work_mode` |
| hr_features.employee_id | hr_attrition.employee_id | `fk_hf_attrition` |
| hr_features.country | dim_country.country | `fk_hf_country` |
| hr_features.department | dim_department.department | `fk_hf_department` |
| hr_features.job_title | dim_job_title.job_title | `fk_hf_job_title` |
| hr_features.status | dim_status.status | `fk_hf_status` |
| hr_features.talent_segment | dim_talent_segment.talent_segment | `fk_hf_talent_segment` |
| hr_features.work_mode | dim_work_mode.work_mode | `fk_hf_work_mode` |

### JOIN proof

Execution time: **68.430s**

| talent_segment | employees |
|---|---:|
| Standard / Low Perf | 1,239,540 |
| Stable Workforce | 342,403 |
| High Flight Risk (Underpaid Star) | 218,778 |
| Lost Star Talent | 199,279 |

### EXPLAIN

```
{'id': 1, 'select_type': 'SIMPLE', 'table': 'd', 'partitions': None, 'type': 'index', 'possible_keys': 'PRIMARY', 'key': 'PRIMARY', 'key_len': '134', 'ref': None, 'rows': 4, 'filtered': 100.0, 'extra': 'Using index; Using temporary; Using filesort'}
{'id': 1, 'select_type': 'SIMPLE', 'table': 'f', 'partitions': None, 'type': 'ref', 'possible_keys': 'PRIMARY,idx_hf_talent_segment', 'key': 'idx_hf_talent_segment', 'key_len': '134', 'ref': 'db_hr_mnc.d.talent_segment', 'rows': 1, 'filtered': 100.0, 'extra': 'Using index'}
{'id': 1, 'select_type': 'SIMPLE', 'table': 'a', 'partitions': None, 'type': 'eq_ref', 'possible_keys': 'uq_hr_attrition_employee_id', 'key': 'uq_hr_attrition_employee_id', 'key_len': '1023', 'ref': 'db_hr_mnc.f.employee_id', 'rows': 1, 'filtered': 100.0, 'extra': 'Using where; Using index'}
```
