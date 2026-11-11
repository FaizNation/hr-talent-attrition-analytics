import React, { useEffect, useState } from 'react';
import Navbar from './components/Navbar';
import StatsCards from './components/StatsCards';
import EmployeeSearch from './components/EmployeeSearch';
import DepartmentSection from './components/DepartmentSection';
import WorkModeSection from './components/WorkModeSection';
import JobTitleSection from './components/JobTitleSection';
import {
  fetchOverview,
  fetchDepartments,
  fetchJobTitles,
  fetchWorkModes,
} from './services/api';
import { Loader2, AlertCircle } from 'lucide-react';

export default function App() {
  const [overview, setOverview] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [jobTitles, setJobTitles] = useState([]);
  const [workModes, setWorkModes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadAllData() {
      try {
        setLoading(true);
        const [ovData, deptData, jtData, wmData] = await Promise.all([
          fetchOverview(),
          fetchDepartments(),
          fetchJobTitles(),
          fetchWorkModes(),
        ]);
        setOverview(ovData);
        setDepartments(deptData);
        setJobTitles(jtData);
        setWorkModes(wmData);
        setError(null);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
        setError(err.message || 'Gagal terhubung ke backend Express (Port 5001)');
      } finally {
        setLoading(false);
      }
    }

    loadAllData();
  }, []);

  return (
    <div className="app-container">
      <Navbar />

      {loading && (
        <div style={{ textAlign: 'center', padding: '80px 20px', color: 'var(--text-muted)' }}>
          <Loader2 size={36} className="pulse-dot" style={{ margin: '0 auto 16px auto', display: 'block' }} />
          <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>Memuat data analitik dari MongoDB...</p>
        </div>
      )}

      {error && !loading && (
        <div style={{ padding: '24px', background: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.3)', borderRadius: 'var(--radius-lg)', color: '#fb7185', marginBottom: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.1rem', fontWeight: 700, marginBottom: '8px' }}>
            <AlertCircle size={22} />
            Koneksi Backend Gagal
          </div>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
            Pastikan backend Express sedang berjalan di <code>http://localhost:5001</code>.
            Jalankan <code>npm start</code> di dalam folder <code>app/backend</code>.
          </p>
        </div>
      )}

      {!loading && !error && (
        <main>
          {/* 1. Macro KPI Cards */}
          <StatsCards overview={overview} />

          {/* 2. Live 2-Million Employee Search Engine */}
          <EmployeeSearch />

          {/* 3. Department & Work Mode Grid */}
          <div className="dashboard-grid">
            <DepartmentSection departments={departments} />
            <WorkModeSection workModes={workModes} />
          </div>

          {/* 4. Job Title Salary Explorer */}
          <JobTitleSection jobTitles={jobTitles} />
        </main>
      )}

      <footer style={{ marginTop: '50px', textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-dim)', borderTop: '1px solid var(--border)', paddingTop: '24px' }}>
        HR MNC Big Data Analytics · MySQL (System of Record) + MongoDB 8.2 (NoSQL Serving Layer) + React 19 + Express.js
      </footer>
    </div>
  );
}
