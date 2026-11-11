import React from 'react';
import { Laptop, Briefcase } from 'lucide-react';

export default function WorkModeSection({ workModes }) {
  if (!workModes || workModes.length === 0) return null;

  return (
    <div className="section-card">
      <div className="section-header">
        <h3 className="section-title">
          <Briefcase size={20} color="#3b82f6" />
          Komparasi Work Mode
        </h3>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          On-site vs Remote
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '10px' }}>
        {workModes.map((wm) => {
          const isRemote = wm.work_mode === 'Remote';
          return (
            <div
              key={wm._id}
              style={{
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                padding: '18px',
                textAlign: 'center',
              }}
            >
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '44px',
                  height: '44px',
                  borderRadius: '50%',
                  background: isRemote ? 'rgba(59, 130, 246, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                  color: isRemote ? '#60a5fa' : '#fbbf24',
                  marginBottom: '10px',
                }}
              >
                {isRemote ? <Laptop size={22} /> : <Briefcase size={22} />}
              </div>
              <h4 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '4px' }}>{wm.work_mode}</h4>
              <div style={{ fontSize: '1.35rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--text-main)', marginBottom: '4px' }}>
                {wm.employee_count?.toLocaleString()}
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Pangsa: {wm.share_percentage}%</div>

              <div style={{ borderTop: '1px solid var(--border)', marginTop: '12px', paddingTop: '10px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Rata-rata Gaji: <strong style={{ color: 'var(--text-main)' }}>₹{Math.round(wm.avg_salary_inr || 0).toLocaleString()}</strong>
                <br />
                Rating Kinerja: <strong style={{ color: '#fbbf24' }}>★ {wm.avg_performance_rating}</strong>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
