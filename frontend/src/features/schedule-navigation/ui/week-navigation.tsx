import { addDays, dateLabel } from '@/shared/lib/calendar'

import s from './week-navigation.module.css'

export function WeekNavigation({
  start,
  end,
  onChange,
}: {
  start: string
  end: string
  onChange: (start: string) => void
}) {
  return (
    <div className={s.root}>
      <div className={s.navigation}>
        <button
          className={s.button}
          aria-label="Предыдущая неделя"
          onClick={() => onChange(addDays(start, -7))}
        >
          ‹
        </button>
        <span className={s.label} aria-live="polite">
          {dateLabel(start)} — {dateLabel(end)}
        </span>
        <button
          className={s.button}
          aria-label="Следующая неделя"
          onClick={() => onChange(addDays(start, 7))}
        >
          ›
        </button>
      </div>
    </div>
  )
}
