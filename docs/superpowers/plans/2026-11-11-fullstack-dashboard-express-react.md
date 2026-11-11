# Fullstack HR Analytics Dashboard Implementation Plan (Express + React Vite + MongoDB)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete fullstack application (`app/backend/` and `app/frontend/`) that queries and visualizes the local MongoDB database `db_hr_mnc`, featuring summary dashboards and live sub-millisecond search across all 2,000,000 employee records.

**Architecture:** 
- Backend: Express.js REST API on port 5001 querying MongoDB `db_hr_mnc` using the official `mongodb` native driver.
- Frontend: React + Vite on port 5173 with modern UI styling, interactive metric cards, charts, and a real-time 2-million employee search engine.

**Tech Stack:** Node.js v24, Express 4.x, MongoDB Native Driver, React 19, Vite, Tailwind CSS / Lucide React.

**Spec:** `docs/superpowers/specs/2026-11-11-fullstack-dashboard-express-react-design.md`

## Global Constraints

- Port assignments: Backend runs on `5001` (to prevent conflicts); Frontend runs on `5173`.
- Data source: MongoDB `db_hr_mnc` (collections: `employees` [2M docs], `hr_overview_summary`, `department_summary`, `job_title_summary`, `work_mode_summary`).
- Performance: Employee ID lookup (`/api/employees/:id`) must resolve via indexed `_id` in < 20ms.
- Privacy: Individual employee lookups show raw attributes (`employee_id`, `department`, `job_title`, `hire_date`, `location`, `salary_inr`, `performance_rating`, `experience_years`, `status`, `work_mode`).

## Review Focus

- Invalid employee ID search: `/api/employees/EMP9999999` must return HTTP 404 with a clean JSON `{ error: "Employee not found" }` rather than crashing.
- MongoDB connection failure: Backend server must log a clear connection error and handle reconnects gracefully.
- CORS configuration: Backend must allow cross-origin requests from `http://localhost:5173`.
- Zero lag in frontend search: Search input must handle fast typing and display instant query latency (e.g. `Query took 3ms`).
- Production build: `npm run build` in `app/frontend` must pass without TypeScript/ESLint errors.

---

### Task 1: Express Backend Setup & Endpoints (`app/backend/`)

**Files:**
- Create: `app/backend/package.json`
- Create: `app/backend/.env`
- Create: `app/backend/src/config/db.js`
- Create: `app/backend/src/routes/api.js`
- Create: `app/backend/src/server.js`

**Interfaces:**
- Produces: REST endpoints on `http://localhost:5001/api`:
  - `GET /api/overview`
  - `GET /api/departments`
  - `GET /api/job-titles`
  - `GET /api/work-modes`
  - `GET /api/employees/:id`
  - `GET /api/employees`

- [ ] **Step 1: Initialize `app/backend` and install dependencies**

Run `npm init -y` and install `express`, `cors`, `dotenv`, `mongodb`.

- [ ] **Step 2: Implement MongoDB client pool in `app/backend/src/config/db.js`**

Export `connectDB()` and `getDB()` connecting to `mongodb://localhost:27017/db_hr_mnc`.

- [ ] **Step 3: Implement route handlers in `app/backend/src/routes/api.js`**

Handle overview, departments, job-titles, work-modes, employee lookup by ID (`db.collection('employees').findOne({ _id: req.params.id })`), and paginated employee list.

- [ ] **Step 4: Implement `app/backend/src/server.js`**

Setup Express, CORS, JSON parsing, routes, and start listening on port 5001.

- [ ] **Step 5: Verification test**

Start server in background and run test script querying:
1. `GET /api/overview` (expect 2M headcount)
2. `GET /api/employees/EMP1000000` (expect employee row with row_id ~1,000,000 in < 15ms)
3. `GET /api/employees/NOT_EXIST` (expect HTTP 404)

- [ ] **Step 6: Commit**

```bash
git add app/backend/
git commit -m "feat(backend): implement Express REST API for MongoDB HR analytics"
```

---

### Task 2: Frontend Styling Setup & API Client (`app/frontend/`)

**Files:**
- Modify: `app/frontend/package.json`
- Create: `app/frontend/src/services/api.js`
- Modify: `app/frontend/src/index.css`

**Interfaces:**
- Produces: API client functions `fetchOverview()`, `fetchDepartments()`, `fetchJobTitles()`, `fetchWorkModes()`, `fetchEmployeeById(id)`.

- [ ] **Step 1: Install frontend helper packages**

Install `lucide-react` for modern icons.

- [ ] **Step 2: Implement API client in `app/frontend/src/services/api.js`**

Configured with base URL `http://localhost:5001/api`.

- [ ] **Step 3: Setup clean modern CSS styling in `src/index.css`**

Include modern dark/light slate color variables, glassmorphic card styles, responsive typography, and badge styles.

- [ ] **Step 4: Verification test**

Run a node snippet verifying `api.js` can reach the running backend.

- [ ] **Step 5: Commit**

```bash
git add app/frontend/
git commit -m "feat(frontend): setup API client and modern design system"
```

---

### Task 3: Build Dashboard Summary Components (`app/frontend/`)

**Files:**
- Create: `app/frontend/src/components/Navbar.jsx`
- Create: `app/frontend/src/components/StatsCards.jsx`
- Create: `app/frontend/src/components/DepartmentSection.jsx`
- Create: `app/frontend/src/components/JobTitleSection.jsx`
- Create: `app/frontend/src/components/WorkModeSection.jsx`

**Interfaces:**
- Produces: Reusable UI components displaying analytical summaries from MongoDB.

- [ ] **Step 1: Build `Navbar.jsx` & `StatsCards.jsx`**

Display system status badge (MongoDB connected, 2,000,000 docs) and 4 macro KPI cards (Headcount, Total Payroll, Avg Salary, Experience & Rating).

- [ ] **Step 2: Build `DepartmentSection.jsx` & `WorkModeSection.jsx`**

Display visual progress bars and comparative breakdown for 7 departments and On-site vs Remote split.

- [ ] **Step 3: Build `JobTitleSection.jsx`**

Filterable/searchable table of all 29 roles with min, avg, max salary and headcount.

- [ ] **Step 4: Commit**

```bash
git add app/frontend/src/components/
git commit -m "feat(frontend): add summary metric cards and breakdown components"
```

---

### Task 4: Build Live 2-Million Employee Search Engine (`app/frontend/`)

**Files:**
- Create: `app/frontend/src/components/EmployeeSearch.jsx`
- Modify: `app/frontend/src/App.jsx`

**Interfaces:**
- Produces: Interactive real-time search component capable of querying any ID across the 2,000,000 MongoDB records with instant latency feedback.

- [ ] **Step 1: Implement `EmployeeSearch.jsx`**

- Search input for ID (`EMP0000001` to `EMP2000000`).
- Preset buttons: `[EMP0000001]`, `[EMP0500000]`, `[EMP1000000]`, `[EMP1500000]`, `[EMP2000000]`.
- Measures round-trip query time and displays `Ditemukan dalam X ms via MongoDB Index`.
- Displays full profile card: Name, ID, Department, Job Title, Hire Date, Location, Performance Rating (stars), Experience, Status badge, Work Mode, and formatted Salary INR.

- [ ] **Step 2: Assemble full layout in `app/frontend/src/App.jsx`**

Integrate Navbar, StatsCards, EmployeeSearch, DepartmentSection, WorkModeSection, and JobTitleSection with loading and error states.

- [ ] **Step 3: Run production build test**

Run: `npm run build` in `app/frontend/`.
Expected: Build passes with 0 errors.

- [ ] **Step 4: Commit**

```bash
git add app/frontend/
git commit -m "feat(frontend): implement live 2M employee search and assemble dashboard"
```

---

### Task 5: End-to-End Verification & Documentation

**Files:**
- Create: `app/README.md`

- [ ] **Step 1: Run end-to-end integration test**

Verify backend responds on port 5001 and frontend serves build or dev server on 5173. Test querying `EMP1000000`.

- [ ] **Step 2: Write `app/README.md`**

Provide startup instructions:
1. `cd app/backend && npm start`
2. `cd app/frontend && npm run dev`
3. Features guide and demo instructions for the lecturer.

- [ ] **Step 3: Commit**

```bash
git add app/README.md
git commit -m "docs(app): add comprehensive fullstack application startup guide"
```
