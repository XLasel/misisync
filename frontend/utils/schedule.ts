export type Lesson = {
  id: string; group_name: string; weekday: number; start_time: string; end_time: string;
  subject: string; lesson_type: string; teacher: string; room: string; subgroup: string;
  subgroup_ids: number[]; week_pattern: string; notes: string; raw_text: string;
  source_url: string; source_sheet: string; source_cell: string;
}
export type LessonCard = Lesson & { originals: Lesson[] }

export function scheduleCards(rows: Lesson[], week: string, subgroup: string): LessonCard[] {
  const cards = new Map<string, LessonCard>()
  for (const row of rows) {
    const ids = row.subgroup_ids || []
    if (week !== 'all' && row.week_pattern !== 'all' && row.week_pattern !== week) continue
    if (subgroup !== 'all' && ids.length && !ids.includes(Number(subgroup))) continue
    const key = JSON.stringify([row.group_name, row.weekday, row.start_time, row.end_time,
      row.subject, row.lesson_type, row.teacher, row.room, row.week_pattern, row.notes,
      !ids.length && row.subgroup ? row.subgroup : ''])
    const existing = cards.get(key)
    if (!existing) cards.set(key, { ...row, subgroup_ids: [...ids], originals: [row] })
    else {
      existing.originals.push(row)
      existing.subgroup_ids = !existing.subgroup_ids.length || !ids.length
        ? [] : [...new Set([...existing.subgroup_ids, ...ids])].sort((a, b) => a - b)
      existing.subgroup = existing.subgroup_ids.length ? existing.subgroup_ids.join(', ') + ' подгруппы' : ''
    }
  }
  return [...cards.values()].sort((a, b) => a.weekday - b.weekday || a.start_time.localeCompare(b.start_time) || a.subject.localeCompare(b.subject, 'ru'))
}

export function normalizeGroupSearch(value: string) {
  return value.normalize('NFKC').trim().toLocaleUpperCase('ru').replace(/[–—−]/g, '-').replace(/\s+/g, '')
}
