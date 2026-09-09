import { addDays, dateLabel } from '../../../shared/lib/calendar'
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
    <div className="week-control calendar-control">
      <button aria-label="Предыдущая неделя" onClick={() => onChange(addDays(start, -7))}>
        ‹
      </button>
      <span aria-live="polite">
        {dateLabel(start)} — {dateLabel(end)}
      </span>
      <button aria-label="Следующая неделя" onClick={() => onChange(addDays(start, 7))}>
        ›
      </button>
    </div>
  )
}
