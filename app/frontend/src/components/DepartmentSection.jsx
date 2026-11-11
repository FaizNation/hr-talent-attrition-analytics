import React from 'react';
import { Building2 } from 'lucide-react';

export default function DepartmentSection({ departments }) {
  if (!departments || departments.length === 0) return null;

  return (
    <div className="section-card">
      <div className="section-header">
        <h3 className="section-title">
          <Building2 size={20} color="#6366f1" />
          Distribusi Departemen (7 Divisi)
        </h3>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          SUM: 2,000,000
        </span>
      </div>

      <div>
        {departments.map((dept) => (
          <div key={dept._id} className="dept-item">
            <div className="dept-header">
              <span className="dept-name">{dept.department}</span>
              <span className="dept-stat">
                {dept.employee_count?.toLocaleString()} org ({dept.headcount_percentage}%) · Avg: ₹{Math.round(dept.avg_salary_inr || 0).toLocaleString()}
              </span>
            </div>
            <div className="progress-track">
              <div
                className="progress-fill"
                style={{
                  width: `${Math.min(100, (dept.headcount_percentage / 35) * 100)}%`,
                }}
              ></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
