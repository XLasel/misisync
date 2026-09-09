/** The public calendar contract, independent of upstream schedule providers. */
export type Window = { start: string; end: string }
export type Coverage = Window & { weekdays: number[] }
export type SourceInfo = {
  id: string
  label: string
  url: string
  basis: 'dated' | 'weekly_template'
}
export type Group = {
  id: string
  name: string
  institutes: string[]
  education_level: string
  subgroups: number[]
}
export type Evidence = { url: string; label: string; raw_text: string; external_id: string | null }
export type Lesson = {
  id: string
  group_id: string
  date: string
  start_time: string | null
  end_time: string | null
  subject: string
  lesson_type: string
  teachers: string[]
  rooms: string[]
  subgroup_ids: number[]
  subgroup_label: string
  notes: string[]
  warnings: string[]
  evidence: Evidence[]
}
export type Catalog = { revision: string | null; groups: Group[] }
export type Schedule = {
  revision: string | null
  group: Group | null
  source: SourceInfo | null
  coverage: Coverage | null
  window: Window
  available_dates: string[]
  lessons: Lesson[]
  warnings: string[]
  fetched_at: string | null
  stale: boolean
}
export type SyncStatus = {
  revision: string | null
  source: SourceInfo | null
  coverage: Coverage | null
  last_success: string | null
  last_attempt: string | null
  last_error: string | null
  updating: boolean
  configured_source: string
  group_count: number
  lesson_count: number
  warnings: string[]
}
