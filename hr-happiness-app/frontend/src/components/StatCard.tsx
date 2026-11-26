interface StatCardProps {
  label: string
  value: string
  note?: string
  featured?: boolean
}

export function StatCard({ label, value, note, featured = false }: StatCardProps) {
  return (
    <article className={featured ? 'stat-card featured' : 'stat-card'}>
      <p className="eyebrow">{label}</p>
      <p className="stat-value">{value}</p>
      {note && <p className="stat-note">{note}</p>}
    </article>
  )
}
