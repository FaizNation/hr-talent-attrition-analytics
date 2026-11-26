import { useCallback } from 'react'
import { getSummary } from '../api/client'
import { ChartCard } from '../components/ChartCard'
import { Disclaimer, ErrorState, Skeleton } from '../components/Feedback'
import { PageHead } from '../components/PageHead'
import { Donut, HeatmapTable, StackedBars } from '../components/charts'
import { StatCard } from '../components/StatCard'
import { useFetch } from '../hooks/useFetch'
import type { Summary } from '../types'
import { groupToRows } from '../utils/chartData'
import { formatNumber, formatPct, HAPPINESS_LABELS, LABEL_COLORS } from '../utils/format'

const STATUS_COLORS = ['#D9542B', '#0E7A6B', '#8A8F7C']

export function Dashboard() {
  const fetcher = useCallback(() => getSummary(), [])
  const { data, error, loading, reload } = useFetch<Summary>(fetcher)

  return (
    <>
      <PageHead
        eyebrow="Ringkasan · seluruh data karyawan"
        title="Peta kebahagiaan organisasi"
        description="Distribusi status, komposisi indeks kebahagiaan, dan pola gaji terhadap pengalaman."
      />
      {loading && (
        <>
          <Skeleton className="stat-grid" rows={4} />
          <Skeleton className="chart-grid" rows={4} />
        </>
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && (
        <div className="dashboard-stack">
          <div className="stat-grid">
            <StatCard
              label="Total data awal"
              value={formatNumber(data.dataset_info.raw_total_rows)}
              note="Baris sebelum pembersihan"
            />
            <StatCard
              label="Retired dibuang"
              value={formatNumber(data.dataset_info.retired_removed_rows)}
              note={`${formatPct(data.dataset_info.retired_removed_pct)} dari data awal`}
            />
            <StatCard
              label="Data bersih"
              value={formatNumber(data.dataset_info.clean_total_rows)}
              note={`Status: ${data.dataset_info.included_statuses.join(', ')}`}
            />
            <StatCard
              label="Model terbaik"
              value={data.ml_split_evaluation.best_model}
              note={`Split ${data.ml_split_evaluation.split_ratio}`}
              featured
            />
          </div>

          <div className="chart-grid">
            <ChartCard eyebrow="Komposisi" title="Distribusi status" className="span-6">
              <Donut
                data={Object.entries(data.status_distribution).map(([name, stat], index) => ({
                  name,
                  value: stat.percentage,
                  color: STATUS_COLORS[index % STATUS_COLORS.length],
                }))}
                centerValue={formatNumber(data.dataset_info.clean_total_rows)}
                centerLabel="karyawan"
              />
            </ChartCard>
            <ChartCard eyebrow="Indeks" title="Distribusi kebahagiaan" className="span-6">
              <Donut
                data={HAPPINESS_LABELS.map((label) => ({
                  name: label,
                  value: data.happiness_distribution[label]?.percentage ?? 0,
                  color: LABEL_COLORS[label],
                }))}
                centerValue="100%"
                centerLabel="karyawan"
              />
            </ChartCard>

            <ChartCard
              eyebrow="Per departemen"
              title="Komposisi kebahagiaan (100%)"
              className="span-12"
            >
              <StackedBars data={groupToRows(data.happiness_by_department_pct)} />
            </ChartCard>
            <ChartCard eyebrow="Per status" title="Komposisi kebahagiaan" className="span-6">
              <StackedBars data={groupToRows(data.happiness_by_status_pct)} />
            </ChartCard>
            <ChartCard eyebrow="Per mode kerja" title="Komposisi kebahagiaan" className="span-6">
              <StackedBars data={groupToRows(data.happiness_by_work_mode_pct)} />
            </ChartCard>

            <ChartCard
              eyebrow="Gaji × pengalaman"
              title="Persentase kategori Bahagia (%)"
              className="span-12"
            >
              <HeatmapTable matrix={data.happiness_heatmap_salary_x_exp_pct} />
            </ChartCard>
          </div>
          <Disclaimer />
        </div>
      )}
    </>
  )
}
