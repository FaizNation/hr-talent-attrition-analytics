import type { HappinessLabel } from '../types'

export const HAPPINESS_LABELS: HappinessLabel[] = [
  'Tidak Bahagia',
  'Cukup Bahagia',
  'Bahagia',
]

export const LABEL_COLORS: Record<HappinessLabel, string> = {
  'Tidak Bahagia': '#EF4444',
  'Cukup Bahagia': '#3B82F6',
  Bahagia: '#10B981',
}

const numberId = new Intl.NumberFormat('id-ID')
const percentId = new Intl.NumberFormat('id-ID', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export const formatNumber = (value: number) => numberId.format(value)
export const formatPct = (value: number) => `${percentId.format(value)}%`
export const formatINR = (value: number) => `₹ ${numberId.format(Math.round(value))}`

export function formatCell(
  value: string | number | boolean | null,
  isPercent = false,
): string {
  if (value === null) return '—'
  if (typeof value !== 'number') return String(value)
  if (isPercent) return formatPct(value)
  return Number.isInteger(value) ? numberId.format(value) : percentId.format(value)
}
