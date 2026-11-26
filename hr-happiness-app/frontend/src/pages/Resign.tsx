import { useCallback } from 'react'
import { getSummary } from '../api/client'
import { ChartCard } from '../components/ChartCard'
import { ErrorState, Skeleton } from '../components/Feedback'
import { GenericTable } from '../components/GenericTable'
import { PageHead } from '../components/PageHead'
import { StatCard } from '../components/StatCard'
import { useFetch } from '../hooks/useFetch'
import type { Summary } from '../types'
import { formatNumber } from '../utils/format'

export function Resign() {
  const fetcher = useCallback(() => getSummary(), [])
  const { data, error, loading, reload } = useFetch<Summary>(fetcher)

  return (
    <>
      <PageHead
        eyebrow="Analisis deskriptif"
        title="Pola pada karyawan yang telah keluar"
        description="Ringkasan faktor dan indikasi yang menyertai status keluar dalam data historis."
      />
      {loading && (
        <>
          <Skeleton className="stat-grid" rows={1} />
          <Skeleton className="chart-grid" rows={2} />
        </>
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && (
        <>
          <p className="method-note">
            Seluruh angka di bawah merangkum data yang sudah terjadi. Analisis ini deskriptif,
            bukan sebuah prediksi.
          </p>
          <div className="stat-grid single">
            <StatCard
              label="Total karyawan keluar"
              value={formatNumber(data.resign_cause_identification.resigned_total)}
              note="Status Resigned pada data bersih"
              featured
            />
          </div>
          <div className="chart-grid">
            <ChartCard
              eyebrow="Faktor utama"
              title="Dominant factors"
              className="span-12"
            >
              <GenericTable records={data.resign_cause_identification.dominant_factors} />
            </ChartCard>
            <ChartCard
              eyebrow="Indikasi bersamaan"
              title="Multi-factor prevalence"
              className="span-12"
            >
              <GenericTable records={data.resign_cause_identification.multi_factor_prevalence} />
            </ChartCard>
          </div>
        </>
      )}
    </>
  )
}
