import { academicWeekReference } from '@/shared/config/academic-week'
import { dateLabel } from '@/shared/lib/calendar'

import { estimateWeekKind } from '../model/academic-week'

import s from './week-estimate.module.css'

export function WeekEstimate({ date }: { date: string }) {
  const label = estimateWeekKind(date) === 'lower' ? 'Нижняя' : 'Верхняя'
  const referenceLabel = academicWeekReference.kind === 'lower' ? 'нижней' : 'верхней'
  return (
    <details className={s.root}>
      <summary className={s.label}>
        <span aria-live="polite">{label} неделя · предположительно</span>
      </summary>
      <p className={s.description}>
        Чередуем недели от {dateLabel(academicWeekReference.date)}{' '}
        {academicWeekReference.date.slice(0, 4)} ({referenceLabel}). Это оценка, а не отметка МИСИС:
        после каникул возможен сдвиг. Уточняйте в объявлениях института и{' '}
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
