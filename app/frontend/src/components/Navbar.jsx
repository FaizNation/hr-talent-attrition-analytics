import React from 'react';
import { Database, Server } from 'lucide-react';

export default function Navbar() {
  return (
    <header className="navbar">
      <div className="brand-wrapper">
        <div className="brand-icon">
          <Database size={24} />
        </div>
        <div>
          <h1 className="brand-title">HR MNC Big Data Analytics</h1>
          <p className="brand-subtitle">
            MongoDB 8.2 NoSQL Serving Layer · Polyglot Persistence Architecture
          </p>
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <a
          href="http://localhost:5001/api-docs/"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(99, 102, 241, 0.15)',
            border: '1px solid rgba(99, 102, 241, 0.3)',
            color: '#a5b4fc',
            padding: '6px 14px',
            borderRadius: 'var(--radius-pill)',
            fontSize: '0.78rem',
            fontWeight: 600,
            textDecoration: 'none',
            transition: 'all 0.2s ease',
          }}
        >
          <Server size={14} />
          <span>Swagger API Docs</span>
        </a>
        <div className="system-badge">
          <span className="pulse-dot"></span>
          <span>2,000,000 DOCS LIVE</span>
        </div>
      </div>
    </header>
  );
}
