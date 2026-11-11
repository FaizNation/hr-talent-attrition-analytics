import React, { useState } from 'react';
import { Layers, Search } from 'lucide-react';

export default function JobTitleSection({ jobTitles }) {
  const [filter, setFilter] = useState('');

  if (!jobTitles || jobTitles.length === 0) return null;

  const filteredTitles = jobTitles.filter(
    (jt) =>
      jt.job_title?.toLowerCase().includes(filter.toLowerCase()) ||
      jt.department?.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="section-card" style={{ marginTop: '28px' }}>
      <div className="section-header" style={{ flexWrap: 'wrap', gap: '14px' }}>
        <h3 className="section-title">
          <Layers size={20} color="#a855f7" />
          Statistik 29 Jabatan (Job Titles Benchmark)
        </h3>

        <div style={{ position: 'relative', minWidth: '240px' }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '11px', color: 'var(--text-dim)' }} />
          <input
            type="text"
            placeholder="Cari jabatan atau departemen..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{
              width: '100%',
              padding: '8px 12px 8px 36px',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-main)',
              fontSize: '0.85rem',
            }}
          />
        </div>
      </div>

      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th>Jabatan (Job Title)</th>
              <th>Departemen</th>
              <th>Headcount</th>
              <th>Min Gaji</th>
              <th>Rata-rata Gaji</th>
              <th>Max Gaji</th>
              <th>Rata-rata Pengalaman</th>
            </tr>
          </thead>
          <tbody>
            {filteredTitles.map((jt) => (
              <tr key={jt._id}>
                <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>{jt.job_title}</td>
                <td>
                  <span className="badge" style={{ background: 'rgba(99, 102, 241, 0.1)', color: '#818cf8' }}>
                    {jt.department}
                  </span>
                </td>
                <td className="mono-cell">{jt.employee_count?.toLocaleString()}</td>
                <td className="mono-cell" style={{ color: '#9ca3af' }}>₹{jt.min_salary_inr?.toLocaleString()}</td>
                <td className="mono-cell" style={{ fontWeight: 600, color: '#34d399' }}>
                  ₹{Math.round(jt.avg_salary_inr || 0).toLocaleString()}
                </td>
                <td className="mono-cell" style={{ color: '#9ca3af' }}>₹{jt.max_salary_inr?.toLocaleString()}</td>
                <td className="mono-cell">{jt.avg_experience_years} thn</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
