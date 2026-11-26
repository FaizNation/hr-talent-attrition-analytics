interface PageHeadProps {
  eyebrow: string
  title: string
  description: string
}

export function PageHead({ eyebrow, title, description }: PageHeadProps) {
  return (
    <header className="page-head">
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      <p className="page-description">{description}</p>
    </header>
  )
}
