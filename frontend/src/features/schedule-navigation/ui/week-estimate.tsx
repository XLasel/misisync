import type { AcademicWeek } from '@/entities/schedule/model/types'
import { dateLabel } from '@/shared/lib/calendar'

import s from './week-estimate.module.css'

export function WeekEstimate({ week }: { week: AcademicWeek }) {
  const label = week.kind === 'lower' ? 'Нижняя' : 'Верхняя'
  const referenceLabel = week.reference_kind === 'lower' ? 'нижней' : 'верхней'
  return (
    <details className={s.root}>
      <summary className={s.label}>
        <span aria-live="polite">{label} неделя · предположительно</span>
      </summary>
      <p className={s.description}>
        Чередуем недели от {dateLabel(week.reference_date)} {week.reference_date.slice(0, 4)} (
        {referenceLabel}). Это оценка, а не отметка МИСИС: после каникул возможен сдвиг. Уточняйте в
        объявлениях института и{' '}
        <a
          href="https://edu.misis.ru/schedule?filial=MOSCOW"
          target="_blank"
          rel="noopener noreferrer"
        >
          расписанием университета
        </a>
        .
      </p>
    </details>
  )
}
