import React, { useState } from 'react';
import { Search, Zap, CheckCircle2, AlertCircle, User, Briefcase, MapPin, Calendar, Star, DollarSign } from 'lucide-react';
import { fetchEmployeeById } from '../services/api';

const PRESETS = [
  'EMP0000001',
  'EMP0500000',
  'EMP1000000',
  'EMP1500000',
  'EMP2000000',
];

export default function EmployeeSearch() {
  const [query, setQuery] = useState('EMP1000000');
  const [employee, setEmployee] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async (targetId) => {
    const idToSearch = (targetId || query).trim().toUpperCase();
    if (!idToSearch) return;

    setLoading(true);
    setError(null);

    try {
      const data = await fetchEmployeeById(idToSearch);
      setEmployee(data);
    } catch (err) {
      setError(err.message);
      setEmployee(null);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="search-card">
      <div className="search-title-row">
        <h3 className="search-title">
          <Zap size={22} color="#818cf8" />
          Live 2-Million Employee Search Engine
        </h3>
        {employee && (
          <span className="search-latency-badge">
            <CheckCircle2 size={13} style={{ display: 'inline', marginRight: '4px', verticalAlign: '-1px' }} />
            O(1) Index Lookup: {employee.latency_ms} ms
          </span>
        )}
      </div>

      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '14px' }}>
        Kueri langsung ke 2.000.000 dokumen MongoDB lokal. Masukkan ID dari <code>EMP0000001</code> hingga <code>EMP2000000</code>:
      </p>

      <div className="search-box">
        <input
          type="text"
          className="search-input"
          placeholder="Masukkan Employee ID (misal: EMP1000000)..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className="search-btn" onClick={() => handleSearch()} disabled={loading}>
          <Search size={18} />
          {loading ? 'Mencari...' : 'Cari Data'}
        </button>
      </div>

      {/* Quick Demo Preset Chips */}
      <div className="presets-row">
        <span className="presets-label">Contoh Demo Cepat:</span>
        {PRESETS.map((p) => (
          <button
            key={p}
            className="preset-chip"
            onClick={() => {
              setQuery(p);
              handleSearch(p);
            }}
          >
            {p}
          </button>
        ))}
      </div>

      {/* Error state */}
      {error && (
        <div style={{ marginTop: '16px', padding: '12px 16px', background: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.3)', borderRadius: 'var(--radius-md)', color: '#fb7185', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.88rem' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Result Card */}
      {employee && (
        <div className="employee-card">
          <div>
            <div className="emp-field-label">Nama Karyawan</div>
            <div className="emp-field-val" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <User size={16} color="#818cf8" />
              {employee.full_name}
            </div>
          </div>

          <div>
            <div className="emp-field-label">Employee ID & Row</div>
            <div className="emp-field-val mono" style={{ color: '#38bdf8' }}>
              {employee.employee_id} (Baris #{employee.row_id?.toLocaleString()})
            </div>
          </div>

          <div>
            <div className="emp-field-label">Departemen & Jabatan</div>
            <div className="emp-field-val" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Briefcase size={16} color="#34d399" />
              {employee.job_title} · <span style={{ color: 'var(--text-muted)' }}>{employee.department}</span>
            </div>
          </div>

          <div>
            <div className="emp-field-label">Gaji Tahunan (INR)</div>
            <div className="emp-field-val mono" style={{ color: '#34d399', fontSize: '1.2rem' }}>
              ₹{employee.salary_inr?.toLocaleString()}
            </div>
          </div>

          <div>
            <div className="emp-field-label">Status & Work Mode</div>
            <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
              <span className={`badge ${employee.status === 'Active' ? 'badge-active' : 'badge-resigned'}`}>
                {employee.status}
              </span>
              <span className={`badge ${employee.work_mode === 'Remote' ? 'badge-remote' : 'badge-onsite'}`}>
                {employee.work_mode}
              </span>
            </div>
          </div>

          <div>
            <div className="emp-field-label">Kinerja & Pengalaman</div>
            <div className="emp-field-val">
              <span style={{ color: '#fbbf24' }}>★ {employee.performance_rating} / 5</span> · {employee.experience_years} Thn
            </div>
          </div>

          <div>
            <div className="emp-field-label">Tanggal Masuk (Hire Date)</div>
            <div className="emp-field-val mono" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.95rem' }}>
              <Calendar size={15} color="var(--text-dim)" />
              {employee.hire_date}
            </div>
          </div>

          <div>
            <div className="emp-field-label">Lokasi Kantor / Kota</div>
            <div className="emp-field-val" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.95rem' }}>
              <MapPin size={15} color="var(--text-dim)" />
              {employee.location}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
