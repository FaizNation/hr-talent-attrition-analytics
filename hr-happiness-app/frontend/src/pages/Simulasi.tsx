import { useCallback } from 'react'
import { getOptions } from '../api/client'
import { SimulationForm } from '../components/SimulationForm'
import { Disclaimer, ErrorState, Skeleton } from '../components/Feedback'
import { PageHead } from '../components/PageHead'
import { useFetch } from '../hooks/useFetch'
import type { Options } from '../types'

export function Simulasi() {
  const fetcher = useCallback(() => getOptions(), [])
  const { data, error, loading, reload } = useFetch<Options>(fetcher)

  return (
    <>
      <PageHead
        eyebrow="Simulasi individual"
        title="Uji satu profil karyawan"
        description="Pilih peran dan isi profil untuk melihat estimasi indeks kebahagiaan berbasis fitur gaji dan masa kerja."
      />
      {loading && <Skeleton className="simulation-grid" rows={5} />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && (
        <>
          <SimulationForm options={data} />
          <Disclaimer />
        </>
      )}
    </>
  )
}
