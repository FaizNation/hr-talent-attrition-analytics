import type { GroupPct, HappinessLabel } from '../types'

export type BarRow = { name: string } & Record<HappinessLabel, number>

export function groupToRows(group: GroupPct): BarRow[] {
  return Object.entries(group).map(([name, values]) => ({
    name,
    'Tidak Bahagia': values['Tidak Bahagia'] ?? 0,
    'Cukup Bahagia': values['Cukup Bahagia'] ?? 0,
    Bahagia: values.Bahagia ?? 0,
  }))
}
