# Fullstack HR Analytics Dashboard Design (Express + React Vite + MongoDB)

Date: 2026-11-11
Status: proposed (awaiting user approval)

## Intent

Build a production-grade fullstack web application for the **HR MNC Analytics** system:
- **Parent Directory:** `app/`
- **Backend (`app/backend/`):** Node.js + Express.js API connected to local MongoDB 8.2 (`db_hr_mnc`).
- **Frontend (`app/frontend/`):** React 18+ + Vite + Tailwind CSS + Lucide Icons + Chart visualizations.

---

## Architecture & Data Flow

```
                      +-----------------------------+
                      |   MongoDB 8.2 (db_hr_mnc)   |
                      |   - employees (2,000,000)   |
                      |   - 4 Summary Collections   |
                      +-----------------------------+
                                     │
                                     ▼ (Native MongoDB Driver, O(1) query)
                      +-----------------------------+
                      |   Backend API (Express.js)  |
                      |   Port: 5001                |
                      +-----------------------------+
                                     │
                                     ▼ REST JSON APIs
                      +-----------------------------+
                      |   Frontend (React + Vite)   |
                      |   Port: 5173                |
                      +-----------------------------+
```

---

## 1. Backend API (`app/backend/`)

- **Port:** `5001` (to avoid conflict with 5000)
- **Tech Stack:** Node.js, Express, `mongodb` (official driver), `cors`, `dotenv`.
- **Endpoints:**
  1. `GET /api/overview` — returns global macro summary (2M headcount, total payroll, status distribution).
  2. `GET /api/departments` — returns 7 department breakdown documents.
  3. `GET /api/job-titles` — returns 29 role salary benchmarks.
  4. `GET /api/work-modes` — returns 2 work mode distributions.
  5. `GET /api/employees` — paginated search & filter across 2,000,000 documents (`?page=1&limit=20&department=IT&search=...`).
  6. `GET /api/employees/:id` — O(1) indexed lookup by `employee_id` (e.g. `/api/employees/EMP1000000`).

---

## 2. Frontend Interface (`app/frontend/`)

- **Port:** `5173` (Vite)
- **Tech Stack:** React 18, Vite, Tailwind CSS, Lucide React, Chart.js / Recharts.
- **Key Features & UI Views:**
  1. **Header & Status Bar:** System status indicator (MongoDB connected, 2,000,000 records live).
  2. **Macro KPI Cards:** 4 high-impact metric cards (Headcount 2M, Total Payroll, Avg Salary, Avg Experience & Rating).
  3. **Interactive Charts:**
     - Headcount & Payroll Allocation by Department (Bar/Doughnut).
     - Work Mode Split (On-site vs Remote).
  4. **Job Title Explorer (29 Roles):** Filterable table with salary bounds (min, median, max) and experience.
  5. **Live 2-Million Employee Search Engine:**
     - Search input allowing the lecturer or user to enter any ID from 1 to 2,000,000 (`EMP0000001` to `EMP2000000`).
     - Quick demo buttons: `[EMP0000001]`, `[EMP0500000]`, `[EMP1000000]`, `[EMP2000000]`.
     - Displays full employee profile card in real-time with latency benchmark (< 5ms).

---

## 3. Directory Structure

```
app/
├── backend/
│   ├── src/
│   │   ├── config/db.js          # MongoDB connection pool
│   │   ├── controllers/hr.js     # Route handlers for summaries and employees
│   │   ├── routes/api.js         # API endpoint definitions
│   │   └── server.js             # Express app entrypoint
│   ├── .env.example
│   └── package.json
└── frontend/
    ├── src/
    │   ├── components/           # Navbar, StatsCard, Charts, SearchBar, EmployeeModal
    │   ├── services/api.js       # Fetch client connecting to backend
    │   ├── App.jsx               # Main dashboard layout
    │   ├── main.jsx
    │   └── index.css             # Tailwind styling
    ├── index.html
    ├── package.json
    ├── tailwind.config.js
    └── vite.config.js
```
