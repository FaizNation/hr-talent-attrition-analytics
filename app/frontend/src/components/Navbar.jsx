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
      <div className="system-badge">
        <span className="pulse-dot"></span>
        <span>2,000,000 DOCS LIVE</span>
      </div>
    </header>
  );
}
