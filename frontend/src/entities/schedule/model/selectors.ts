import type { Lesson } from './types'

export function scheduleCards(rows: Lesson[], subgroup: string): Lesson[] {
  const cards = new Map<string, Lesson>()
  for (const row of rows) {
    const ids = row.subgroup_ids
    if (subgroup !== 'all' && ids.length && !ids.includes(Number(subgroup))) continue
    const key = JSON.stringify([
      row.group_id,
      row.date,
      row.start_time,
      row.end_time,
      row.subject,
      row.lesson_type,
      row.teachers,
      row.rooms,
      row.notes,
      row.warnings,
      !ids.length ? row.subgroup_label : '',
    ])
    const existing = cards.get(key)
    if (!existing) cards.set(key, { ...row, subgroup_ids: [...ids], evidence: [...row.evidence] })
    else {
      existing.evidence.push(...row.evidence)
      existing.subgroup_ids =
        !existing.subgroup_ids.length || !ids.length
          ? []
          : [...new Set([...existing.subgroup_ids, ...ids])].sort((a, b) => a - b)
    }
  }
  return [...cards.values()].sort(
    (a, b) =>
      a.date.localeCompare(b.date) ||
      (a.start_time || '99:99').localeCompare(b.start_time || '99:99') ||
      a.subject.localeCompare(b.subject, 'ru'),
  )
}
