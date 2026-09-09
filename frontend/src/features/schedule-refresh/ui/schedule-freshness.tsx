import { useId } from 'react'
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
    <div className="schedule-freshness">
      <details className="freshness-details">
        <summary>
          Данные расписания{' '}
          <span>
            {label ? `${label} МСК${stale ? ' · сохранённая версия' : ''}` : 'Ещё не получены'}
          </span>
        </summary>
        <p id={id}>
          Время последнего получения данных у университета. «Обновить» повторяет загрузку через
          Misisync: свежий кэш возвращается сразу, после истечения срока бэкенд обращается к МИСИС.
          По умолчанию кэш действует 15 минут.
        </p>
      </details>
      <button
        className="refresh-button"
        disabled={pending}
        aria-describedby={id}
        onClick={onRefresh}
      >
        <span aria-hidden="true">↻</span> {pending ? 'Загрузка…' : 'Обновить'}
      </button>
    </div>
  )
}
