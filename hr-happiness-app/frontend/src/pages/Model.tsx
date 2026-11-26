import { useCallback } from 'react'
import { getSummary } from '../api/client'
import { ChartCard } from '../components/ChartCard'
import { ErrorState, Skeleton } from '../components/Feedback'
import { PageHead } from '../components/PageHead'
import { ModelBars } from '../components/charts'
import { useFetch } from '../hooks/useFetch'
import type { Summary } from '../types'
import { formatPct } from '../utils/format'

export function Model() {
  const fetcher = useCallback(() => getSummary(), [])
  const { data, error, loading, reload } = useFetch<Summary>(fetcher)

  return (
    <>
      <PageHead
        eyebrow="Evaluasi · split internal"
        title="Perbandingan model"
        description="Akurasi dan F1-Macro dari model yang diuji pada split data yang sama."
      />
      {loading && <Skeleton className="chart-grid" rows={2} />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && (
        <div className="chart-grid">
          <div className="meta-strip span-12">
            <span>
              <small>Split</small>
              <b>{data.ml_split_evaluation.split_ratio}</b>
            </span>
            <span>
              <small>Model terbaik</small>
              <b>{data.ml_split_evaluation.best_model}</b>
            </span>
          </div>
          <ChartCard eyebrow="Tabel metrik" title="Hasil per model" className="span-5">
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Model</th>
                    <th scope="col">Accuracy</th>
                    <th scope="col">F1-Macro</th>
                  </tr>
                </thead>
                <tbody>
                  {data.ml_split_evaluation.models.map((model) => (
                    <tr
                      key={model.Model}
                      className={model.Model === data.ml_split_evaluation.best_model ? 'best-row' : undefined}
                    >
                      <td>
                        {model.Model}
                        {model.Model === data.ml_split_evaluation.best_model && (
                          <span className="best-tag">Terbaik</span>
                        )}
                      </td>
                      <td>{formatPct(model['Accuracy (%)'])}</td>
                      <td>{formatPct(model['F1_Macro (%)'])}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </ChartCard>
          <ChartCard eyebrow="Visualisasi" title="Accuracy vs F1-Macro" className="span-7">
            <ModelBars models={data.ml_split_evaluation.models} />
          </ChartCard>
        </div>
      )}
    </>
  )
}
