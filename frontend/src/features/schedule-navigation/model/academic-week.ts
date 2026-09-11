import { academicWeekReference, type WeekKind } from '../../../shared/config/academic-week'
import { mondayOf } from '../../../shared/lib/calendar'

export function estimateWeekKind(date: string, reference = academicWeekReference): WeekKind {
  const offset = Math.round(
    (Date.parse(mondayOf(date)) - Date.parse(mondayOf(reference.date))) / (7 * 86400000),
  )
  return offset % 2 === 0 ? reference.kind : reference.kind === 'lower' ? 'upper' : 'lower'
}
