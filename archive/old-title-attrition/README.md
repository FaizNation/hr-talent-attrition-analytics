# Old Title Archive: HR Talent & Attrition Analytics

This directory contains code and components from the earlier research iteration focused on **employee attrition risk and talent segmentation**.

## Status: Superseded / Archived

This work is preserved for audit trail and historical reference. It is **not** runnable against the current normalized raw SQL schema (`hr_employee` + 4 dimensions).

The active system uses the **Workforce Cost & Startup Runway Simulator** architecture:
- **Relational Data Layer:** MySQL (`db_hr_mnc`) storing only the normalized raw 12 Kaggle dataset columns in `hr_employee` + 4 dimensions.
- **Analytics & Feature Engineering:** `Startup_Runway_Workforce_Simulator_KDD.ipynb` generating runway metrics, effective monthly cost, and talent archetypes exported into `artifacts_runway/`.
- **Backend API:** Flask (`backend_api/`) serving runway simulation and workforce cost endpoints directly from the generated runway artifacts.
- **Frontend Dashboard:** Modern interactive runway simulator in `fe-runway/`.

## Archived Artifacts

- `nosql/`: Firebase Realtime Database extraction and upload pipeline (`extract_from_mysql.py`, `upload_to_firebase.py`, `verify_firebase.py`). Targeted old `hr_features` and `branch_efficiency` tables.
- `fe-hr-talent-analytics/`: React Vite dashboard for attrition risk, branch efficiency, and talent segment visualizations.
