import { useMemo, useState } from 'react'
import type { CSSProperties, FormEvent } from 'react'
import { ApiError, postPredict } from '../api/client'
import type { Options, Prediction, PredictionInput } from '../types'
import { formatNumber, formatPct, HAPPINESS_LABELS, LABEL_COLORS } from '../utils/format'
import { LabelBadge } from './LabelBadge'

interface FormState {
  department: string
  job_title: string
  salary_inr: string
  experience_years: string
  tenure_years: string
}

type FieldErrors = Partial<Record<keyof FormState, string>>

const EMPTY_FORM: FormState = {
  department: '',
  job_title: '',
  salary_inr: '',
  experience_years: '',
  tenure_years: '',
}

function validate(form: FormState): FieldErrors {
  const errors: FieldErrors = {}
  if (!form.department.trim()) errors.department = 'Pilih department.'
  if (!form.job_title.trim()) errors.job_title = 'Pilih job title.'

  const salary = Number(form.salary_inr)
  if (!form.salary_inr.trim() || !Number.isFinite(salary) || salary <= 0) {
    errors.salary_inr = 'Gaji harus berupa angka lebih dari 0.'
  }

  for (const field of ['experience_years', 'tenure_years'] as const) {
    const raw = form[field]
    const value = Number(raw)
    if (!raw.trim() || !Number.isInteger(value) || value < 0) {
      errors[field] = 'Harus bilangan bulat lebih dari atau sama dengan 0.'
    }
  }
  return errors
}

export function SimulationForm({ options }: { options: Options }) {
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [result, setResult] = useState<Prediction | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [lastPayload, setLastPayload] = useState<PredictionInput | null>(null)

  const jobTitles = useMemo(
    () => (form.department ? options.job_titles_by_department[form.department] ?? [] : []),
    [options, form.department],
  )

  const update = (field: keyof FormState, value: string) => {
    setForm((current) => ({ ...current, [field]: value }))
    setFieldErrors((current) => ({ ...current, [field]: undefined }))
  }

  const submit = async (payload: PredictionInput) => {
    setLoading(true)
    setError(null)
    try {
      setResult(await postPredict(payload))
    } catch (reason) {
      setResult(null)
      if (reason instanceof ApiError) {
        if (reason.details) {
          setFieldErrors((current) => ({ ...current, ...reason.details }))
        }
        setError(reason.message)
      } else {
        setError('Terjadi kesalahan saat menjalankan simulasi. Silakan coba lagi.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const errors = validate(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    const payload: PredictionInput = {
      department: form.department.trim(),
      job_title: form.job_title.trim(),
      salary_inr: Number(form.salary_inr),
      experience_years: Number(form.experience_years),
      tenure_years: Number(form.tenure_years),
    }
    setLastPayload(payload)
    void submit(payload)
  }

  const download = () => {
    if (!result) return
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' }),
    )
    const link = document.createElement('a')
    link.href = url
    link.download = 'ehi-hasil-simulasi.json'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="simulation-grid">
      <form className="sim-form" onSubmit={handleSubmit} noValidate>
        <div className="form-head">
          <p className="eyebrow">Input karyawan</p>
          <h2>Profil simulasi</h2>
        </div>

        <label className="field">
          <span>Department</span>
          <select
            value={form.department}
            onChange={(event) => {
              update('department', event.target.value)
              update('job_title', '')
            }}
            aria-invalid={Boolean(fieldErrors.department)}
          >
            <option value="">Pilih department</option>
            {options.departments.map((department) => (
              <option key={department} value={department}>
                {department}
              </option>
            ))}
          </select>
          {fieldErrors.department && <small className="field-error">{fieldErrors.department}</small>}
        </label>

        <label className="field">
          <span>Job title</span>
          <select
            value={form.job_title}
            onChange={(event) => update('job_title', event.target.value)}
            disabled={!form.department}
            aria-invalid={Boolean(fieldErrors.job_title)}
          >
            <option value="">{form.department ? 'Pilih job title' : 'Pilih department dulu'}</option>
            {jobTitles.map((title) => (
              <option key={title} value={title}>
                {title}
              </option>
            ))}
          </select>
          {fieldErrors.job_title && <small className="field-error">{fieldErrors.job_title}</small>}
        </label>

        <label className="field">
          <span>Gaji tahunan (INR)</span>
          <input
            type="number"
            min="1"
            step="any"
            value={form.salary_inr}
            onChange={(event) => update('salary_inr', event.target.value)}
            placeholder="1200000"
            aria-invalid={Boolean(fieldErrors.salary_inr)}
          />
          {fieldErrors.salary_inr && <small className="field-error">{fieldErrors.salary_inr}</small>}
        </label>

        <div className="field-pair">
          <label className="field">
            <span>Pengalaman (tahun)</span>
            <input
              type="number"
              min="0"
              step="1"
              value={form.experience_years}
              onChange={(event) => update('experience_years', event.target.value)}
              placeholder="3"
              aria-invalid={Boolean(fieldErrors.experience_years)}
            />
            {fieldErrors.experience_years && (
              <small className="field-error">{fieldErrors.experience_years}</small>
            )}
          </label>
          <label className="field">
            <span>Masa kerja (tahun)</span>
            <input
              type="number"
              min="0"
              step="1"
              value={form.tenure_years}
              onChange={(event) => update('tenure_years', event.target.value)}
              placeholder="2"
              aria-invalid={Boolean(fieldErrors.tenure_years)}
            />
            {fieldErrors.tenure_years && (
              <small className="field-error">{fieldErrors.tenure_years}</small>
            )}
          </label>
        </div>

        {error && (
          <div className="form-error" role="alert">
            <span>{error}</span>
            {lastPayload && (
              <button type="button" className="button ghost" onClick={() => void submit(lastPayload)}>
                Coba lagi
              </button>
            )}
          </div>
        )}

        <button type="submit" className="button primary" disabled={loading}>
          {loading ? 'Memproses…' : 'Jalankan simulasi'}
        </button>
      </form>

      <div className="result-column" aria-live="polite">
        {!result && !loading && (
          <div className="result-empty">
            <span className="result-empty-mark">↗</span>
            <p className="eyebrow">Belum ada hasil</p>
            <p>Isi profil karyawan, lalu jalankan simulasi untuk melihat estimasi indeks.</p>
          </div>
        )}
        {loading && (
          <div className="result-empty">
            <span className="spinner" aria-hidden="true" />
            <p>Menghitung fitur dan estimasi…</p>
          </div>
        )}
        {result && !loading && (
          <section
            className="result-panel"
            style={{ '--result-color': LABEL_COLORS[result.label] } as CSSProperties}
          >
            <div className="result-topline">
              <span className="eyebrow">Estimasi indeks kebahagiaan</span>
              <LabelBadge label={result.label} />
            </div>
            <p className="result-label">{result.label}</p>

            <div className="probabilities">
              {HAPPINESS_LABELS.map((label) => {
                const percent = (result.probabilities[label] ?? 0) * 100
                return (
                  <div className="prob-row" key={label}>
                    <div className="prob-meta">
                      <span>{label}</span>
                      <b>{formatPct(percent)}</b>
                    </div>
                    <div className="prob-track">
                      <span
                        style={{ width: `${percent}%`, background: LABEL_COLORS[label] }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>

            {result.warnings.length > 0 && (
              <ul className="warning-list">
                {result.warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            )}

            <div className="feature-grid">
              {Object.entries(result.features).map(([name, value]) => (
                <div key={name}>
                  <span>{name}</span>
                  <b>{formatNumber(value)}</b>
                </div>
              ))}
            </div>

            <button type="button" className="button outline" onClick={download}>
              Unduh hasil (JSON)
            </button>
          </section>
        )}
      </div>
    </div>
  )
}
