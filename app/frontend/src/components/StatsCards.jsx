import React from 'react';
import { Users, DollarSign, TrendingUp, Award } from 'lucide-react';

function formatINR(val) {
  if (!val) return '₹0';
  if (val >= 1e12) return `₹${(val / 1e12).toFixed(2)} T`;
  if (val >= 1e7) return `₹${(val / 1e7).toFixed(2)} Cr`;
  if (val >= 1e5) return `₹${(val / 1e5).toFixed(2)} Lakh`;
  return `₹${val.toLocaleString('en-IN')}`;
}

export default function StatsCards({ overview }) {
  if (!overview) return null;

  const statusDist = overview.status_distribution || {};

  return (
    <div>
      <div className="stats-grid">
        {/* Card 1: Total Employees */}
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-title">Total Headcount</span>
            <div className="stat-icon" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>
              <Users size={20} />
            </div>
          </div>
          <div className="stat-val">{overview.total_employees?.toLocaleString()}</div>
          <div className="stat-desc">2 Juta Dokumen Utuh di MongoDB</div>
        </div>

        {/* Card 2: Total Payroll */}
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-title">Total Pengeluaran Gaji</span>
            <div className="stat-icon" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa' }}>
              <DollarSign size={20} />
            </div>
          </div>
          <div className="stat-val">{formatINR(overview.total_payroll_inr)}</div>
          <div className="stat-desc">Per Tahun (INR Currency)</div>
        </div>

        {/* Card 3: Avg Salary */}
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-title">Rata-Rata Gaji</span>
            <div className="stat-icon" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}>
              <TrendingUp size={20} />
            </div>
          </div>
          <div className="stat-val">₹{Math.round(overview.avg_salary_inr || 0).toLocaleString()}</div>
          <div className="stat-desc">
            Min: ₹{(overview.min_salary_inr || 0).toLocaleString()} · Max: ₹{(overview.max_salary_inr || 0).toLocaleString()}
          </div>
        </div>

        {/* Card 4: Avg Performance & Experience */}
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-title">Performa & Pengalaman</span>
            <div className="stat-icon" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24' }}>
              <Award size={20} />
            </div>
          </div>
          <div className="stat-val">
            ★ {overview.avg_performance_rating} <span style={{ fontSize: '1.2rem', color: '#9ca3af' }}>/ 5</span>
          </div>
          <div className="stat-desc">
            Rata-rata Pengalaman: <strong>{overview.avg_experience_years} Tahun</strong>
          </div>
        </div>
      </div>

      {/* Status Distribution Sub-bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '28px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 600 }}>STATUS KARYAWAN:</span>
        {Object.entries(statusDist).map(([status, count]) => {
          const pct = ((count / overview.total_employees) * 100).toFixed(1);
          let badgeClass = 'badge-active';
          if (status === 'Resigned') badgeClass = 'badge-resigned';
          if (status === 'Terminated') badgeClass = 'badge-resigned';
          if (status === 'On Leave') badgeClass = 'badge-onsite';
          return (
            <span key={status} className={`badge ${badgeClass}`} style={{ fontSize: '0.78rem', padding: '5px 12px' }}>
              {status}: {count.toLocaleString()} ({pct}%)
            </span>
          );
        })}
      </div>
    </div>
  );
}
