import type { ReactNode } from 'react'

interface ChartCardProps {
  eyebrow: string
  title: string
  children: ReactNode
  className?: string
}

export function ChartCard({ eyebrow, title, children, className = '' }: ChartCardProps) {
  return (
    <section className={`chart-card ${className}`.trim()}>
      <header className="chart-head">
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
      </header>
      {children}
    </section>
  )
}
