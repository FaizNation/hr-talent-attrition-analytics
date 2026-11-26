export type HappinessLabel = 'Tidak Bahagia' | 'Cukup Bahagia' | 'Bahagia'

export interface DatasetInfo {
  raw_total_rows: number
  retired_removed_rows: number
  retired_removed_pct: number
  clean_total_rows: number
  included_statuses: string[]
  excluded_statuses: string[]
}

export interface StatusStat {
  count: number
  percentage: number
}

export interface HappinessStat {
  count: number
  percentage: number
  avg_salary_inr: number
  avg_experience_years: number
  avg_tenure_years: number
  avg_happiness_score: number
}

export type GenericRecord = Record<string, string | number | boolean | null>

export type GroupPct = Record<string, Partial<Record<HappinessLabel, number>>>

export interface ModelRecord {
  Model: string
  'Accuracy (%)': number
  'Precision_Macro (%)': number
  'Recall_Macro (%)': number
  'F1_Macro (%)': number
  [key: string]: string | number
}

export interface Summary {
  dataset_info: DatasetInfo
  status_distribution: Record<string, StatusStat>
  happiness_distribution: Record<HappinessLabel, HappinessStat>
  resign_cause_identification: {
    resigned_total: number
    multi_factor_prevalence: GenericRecord[]
    dominant_factors: GenericRecord[]
  }
  happiness_by_department_pct: GroupPct
  happiness_by_status_pct: GroupPct
  happiness_by_work_mode_pct: GroupPct
  happiness_heatmap_salary_x_exp_pct: Record<string, Record<string, number>>
  ml_split_evaluation: {
    split_ratio: string
    best_model: string
    models: ModelRecord[]
  }
}

export interface Options {
  departments: string[]
  job_titles_by_department: Record<string, string[]>
}

export interface PredictionInput {
  department: string
  job_title: string
  salary_inr: number
  experience_years: number
  tenure_years: number
}

export interface Prediction {
  label: HappinessLabel
  label_code: number
  probabilities: Record<HappinessLabel, number>
  features: Record<string, number>
  warnings: string[]
}

export interface Health {
  status: string
  model: string
}
