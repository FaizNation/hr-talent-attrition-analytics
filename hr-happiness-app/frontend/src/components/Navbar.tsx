import type { MouseEvent } from 'react'

interface NavbarProps {
  path: string
  model?: string
  onNavigate: (path: string) => void
}

const LINKS = [
  { path: '/', label: 'Dashboard' },
  { path: '/resign', label: 'Analisis Resign' },
  { path: '/simulasi', label: 'Simulasi' },
  { path: '/model', label: 'Evaluasi Model' },
]

export function Navbar({ path, model, onNavigate }: NavbarProps) {
  const handleClick = (event: MouseEvent<HTMLAnchorElement>, target: string) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return
    event.preventDefault()
    onNavigate(target)
  }

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <a className="brand" href="/" onClick={(event) => handleClick(event, '/')}>
          <span className="brand-mark">EHI</span>
          <span className="brand-text">
            <strong>Employee Happiness Index</strong>
            <small>HR MNC · people analytics</small>
          </span>
        </a>
        <nav aria-label="Navigasi utama">
          {LINKS.map((link) => (
            <a
              key={link.path}
              href={link.path}
              className={path === link.path ? 'nav-link active' : 'nav-link'}
              aria-current={path === link.path ? 'page' : undefined}
              onClick={(event) => handleClick(event, link.path)}
            >
              {link.label}
            </a>
          ))}
        </nav>
        <span className="model-chip" title="Model yang dimuat backend">
          <span className="pulse-dot" aria-hidden="true" />
          {model ?? 'model: —'}
        </span>
      </div>
    </header>
  )
}
