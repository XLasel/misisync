export type WeekKind = 'upper' | 'lower'

/** User-confirmed reference, not a value supplied by the university API. */
export const academicWeekReference: { date: string; kind: WeekKind } = {
  date: '2026-09-07',
  kind: 'lower',
}
