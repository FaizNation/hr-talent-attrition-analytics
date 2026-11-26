import type { Health, Options, Prediction, PredictionInput, Summary } from '../types'

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:5000').replace(/\/+$/, '')

export class ApiError extends Error {
  readonly status: number
  readonly details?: Record<string, string>

  constructor(message: string, status: number, details?: Record<string, string>) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (init?.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers })
  } catch {
    throw new ApiError('Backend tidak dapat dijangkau. Pastikan server Flask berjalan.', 0)
  }

  let body: unknown = null
  try {
    body = await response.json()
  } catch {
    // Response tanpa JSON tetap ditangani sebagai error generik di bawah.
  }

  if (!response.ok) {
    const payload = body as { error?: unknown; details?: Record<string, string> } | null
    const message =
      typeof payload?.error === 'string'
        ? payload.error
        : `Permintaan gagal (HTTP ${response.status}).`
    throw new ApiError(message, response.status, payload?.details)
  }
  return body as T
}

export const getHealth = () => request<Health>('/api/health')
export const getOptions = () => request<Options>('/api/options')
export const getSummary = () => request<Summary>('/api/summary')
export const postPredict = (payload: PredictionInput) =>
  request<Prediction>('/api/predict', { method: 'POST', body: JSON.stringify(payload) })
