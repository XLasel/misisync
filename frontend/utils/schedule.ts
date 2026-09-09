import type { Lesson, Schedule, Window } from '../types/schedule'

export function matchesSchedule(schedule: Schedule | null, group: string, window: Window): boolean {
  return schedule?.group?.id === group && schedule.window.start === window.start && schedule.window.end === window.end
}

export function scheduleCards(rows: Lesson[], subgroup: string): Lesson[] {
  const cards = new Map<string, Lesson>()
  for (const row of rows) {
    const ids = row.subgroup_ids
    if (subgroup !== 'all' && ids.length && !ids.includes(Number(subgroup))) continue
    const key = JSON.stringify([row.group_id, row.date, row.start_time, row.end_time,
      row.subject, row.lesson_type, row.teachers, row.rooms, row.notes, row.warnings,
      !ids.length ? row.subgroup_label : ''])
    const existing = cards.get(key)
    if (!existing) cards.set(key, { ...row, subgroup_ids: [...ids], evidence: [...row.evidence] })
    else {
      existing.evidence.push(...row.evidence)
      existing.subgroup_ids = !existing.subgroup_ids.length || !ids.length
        ? [] : [...new Set([...existing.subgroup_ids, ...ids])].sort((a, b) => a - b)
    }
  }
  return [...cards.values()].sort((a, b) => a.date.localeCompare(b.date) ||
    (a.start_time || '99:99').localeCompare(b.start_time || '99:99') || a.subject.localeCompare(b.subject, 'ru'))
}

export function normalizeGroupSearch(value: string) {
  return value.normalize('NFKC').trim().toLocaleUpperCase('ru').replace(/[–—−]/g, '-').replace(/\s+/g, '')
}

export function addDays(iso: string, count: number) {
  const date = new Date(`${iso}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() + count)
  return date.toISOString().slice(0, 10)
}

export function mondayOf(iso: string) {
  return addDays(iso, -((new Date(`${iso}T12:00:00Z`).getUTCDay() + 6) % 7))
}

export function moscowToday() {
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Moscow', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
}
