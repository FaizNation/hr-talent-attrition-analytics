import type { CSSProperties } from 'react'
import type { HappinessLabel } from '../types'
import { LABEL_COLORS } from '../utils/format'

export function LabelBadge({ label }: { label: HappinessLabel }) {
  return (
    <span className="label-badge" style={{ '--badge-color': LABEL_COLORS[label] } as CSSProperties}>
      <span className="badge-dot" aria-hidden="true" />
      {label}
    </span>
  )
}
