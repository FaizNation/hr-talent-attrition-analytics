import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'

/** Fetch dengan state loading/error + reload; fetcher harus stabil (useCallback). */
export function useFetch<T>(fetcher: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)
  const reload = useCallback(() => {
    setLoading(true)
    setError(null)
    setAttempt((value) => value + 1)
  }, [])

  useEffect(() => {
    let active = true
    fetcher()
      .then((result) => {
        if (active) setData(result)
      })
      .catch((reason: unknown) => {
        if (!active) return
        setError(
          reason instanceof ApiError
            ? reason.message
            : 'Terjadi kesalahan saat memuat data. Silakan coba lagi.',
        )
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [fetcher, attempt])

  return { data, error, loading, reload }
}
