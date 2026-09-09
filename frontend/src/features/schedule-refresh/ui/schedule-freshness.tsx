import { useId } from 'react'

import { Button } from '@/shared/ui'

import s from './schedule-freshness.module.css'

export function ScheduleFreshness({
  fetchedAt,
  stale,
  pending,
  onRefresh,
}: {
  fetchedAt: string | null
  stale: boolean
  pending: boolean
  onRefresh: () => void
}) {
  const id = useId()
  const label = fetchedAt
    ? new Intl.DateTimeFormat('ru-RU', {
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'Europe/Moscow',
      }).format(new Date(fetchedAt))
    : null
  return (
    <div className={s.root}>
      <details className={s.details}>
        <summary>
          <span className={s.summary}>
            <span className={s.title}>Данные расписания</span>
            <span className={s.meta}>
              {label ? `${label} МСК${stale ? ' · сохранённая версия' : ''}` : 'Ещё не получены'}
            </span>
          </span>
        </summary>
        <p id={id}>
          Время последнего получения данных у университета. «Обновить» повторяет загрузку через
          Misisync: свежий кэш возвращается сразу, после истечения срока бэкенд обращается к МИСИС.
          По умолчанию кэш действует 15 минут.
        </p>
      </details>
      <Button
        className={s.action}
        variant="secondary"
        disabled={pending}
        aria-describedby={id}
        onClick={onRefresh}
      >
        <span aria-hidden="true">↻</span> {pending ? 'Загрузка…' : 'Обновить'}
      </Button>
    </div>
  )
}
