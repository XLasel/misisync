import { scheduleCards } from '@/entities/schedule/model/selectors'
import type { Group, Schedule } from '@/entities/schedule/model/types'
import { LessonCard } from '@/entities/schedule/ui/lesson-card'
import { WeekEstimate } from '@/features/schedule-navigation/ui/week-estimate'
import { WeekNavigation } from '@/features/schedule-navigation/ui/week-navigation'
import { ScheduleFreshness } from '@/features/schedule-refresh/ui/schedule-freshness'
import { SubgroupFilter } from '@/features/subgroup-filter/ui/subgroup-filter'
import { dateLabel, days, shortDays } from '@/shared/lib/calendar'
import { classNames } from '@/shared/lib/class-names'
import { Button, EmptyState, Overline } from '@/shared/ui'

import s from './schedule-panel.module.css'

type Props = {
  group: Group | null
  schedule: Schedule | null
  dates: string[]
  weekday: number
  subgroup: string
  pending: boolean
  error: string | null
  catalogPending: boolean
  onWeek: (value: string) => void
  onDay: (value: number) => void
  onSubgroup: (value: string) => void
  onRefresh: () => void
}
export function SchedulePanel({
  group,
  schedule,
  dates,
  weekday,
  subgroup,
  pending,
  error,
  catalogPending,
  onWeek,
  onDay,
  onSubgroup,
  onRefresh,
}: Props) {
  const subgroups = [
    ...new Set([
      ...(group?.subgroups || []),
      ...(schedule?.lessons || []).flatMap((l) => l.subgroup_ids),
    ]),
  ].sort((a, b) => a - b)
  const selectedSubgroup = subgroups.includes(Number(subgroup)) ? subgroup : 'all'
  const cards = scheduleCards(schedule?.lessons || [], selectedSubgroup)
  const lessons = cards.filter((l) => l.date === dates[weekday])
  const available = schedule?.available_dates.includes(dates[weekday]!) || false
  let content
  if (error)
    content = (
      <EmptyState symbol="↻" title="Не удалось получить расписание" alert>
        <p>{error}</p>
        <Button onClick={onRefresh}>Повторить</Button>
      </EmptyState>
    )
  else if (!group)
    content = (
      <EmptyState symbol="▦" title="Какая у тебя группа?">
        <p>
          {catalogPending
            ? 'Список групп ещё загружается.'
            : 'Найди её по названию. Мы покажем пары и запомним твой выбор.'}
        </p>
        {!catalogPending && (
          <Button onClick={() => document.getElementById('group-search')?.focus()}>
            Найти группу ↗
          </Button>
        )}
      </EmptyState>
    )
  else if (pending && !schedule) content = <EmptyState symbol="⋯" title="Загружаем занятия" />
  else if (!schedule?.group)
    content = (
      <EmptyState symbol="◷" title="Группа отсутствует в источнике">
        <p>Попробуй выбрать другую группу или обновить страницу.</p>
      </EmptyState>
    )
  else if (!available)
    content = (
      <EmptyState symbol="◷" title="Данные за этот день не загружены">
        <p>Выбери день с понедельника по субботу. Воскресенье в источнике не отдаётся.</p>
      </EmptyState>
    )
  else if (!lessons.length)
    content = (
      <EmptyState symbol="☀" title="В расписании нет занятий">
        <p>Для этого дня, недели и подгруппы пары не указаны в источнике.</p>
      </EmptyState>
    )
  else
    content = (
      <ol className={classNames(s.list, pending && s.refreshing)}>
        {lessons.map((lesson) => (
          <LessonCard key={lesson.id} lesson={lesson} />
        ))}
      </ol>
    )

  return (
    <section className={s.root} aria-label="Расписание занятий" aria-busy={pending}>
      <div className={s.heading}>
        <div>
          <Overline>РАСПИСАНИЕ ЗАНЯТИЙ</Overline>
          <h2>{group?.name || 'Твоя учебная неделя'}</h2>
        </div>
      </div>
      {group && (
        <div className={s.controls}>
          <WeekNavigation start={dates[0]!} end={dates[6]!} onChange={onWeek} />
          <SubgroupFilter values={subgroups} selected={selectedSubgroup} onChange={onSubgroup} />
        </div>
      )}
      {group && (
        <div className={s.weekNote}>
          <WeekEstimate date={dates[0]!} />
        </div>
      )}
      <nav className={s.tabs} aria-label="Дни недели">
        {days.map((day, i) => (
          <button
            key={day}
            aria-label={day}
            aria-pressed={weekday === i}
            className={weekday === i ? s.active : ''}
            onClick={() => onDay(i)}
          >
            <span>{shortDays[i]}</span>
            <span className={s.count}>
              {group && schedule?.available_dates.includes(dates[i]!)
                ? cards.filter((l) => l.date === dates[i]).length
                : '—'}
            </span>
          </button>
        ))}
      </nav>
      <div className={s.day}>
        <h3>
          {days[weekday]} <small>{dateLabel(dates[weekday]!)}</small>
        </h3>
        <span>
          {group && available && !pending ? `Занятий: ${lessons.length}` : 'Время московское'}
        </span>
      </div>
      {selectedSubgroup !== 'all' && group && (
        <p className={s.note}>Подгруппа {selectedSubgroup} и занятия без уточнения подгруппы.</p>
      )}
      {schedule?.warnings.map((warning) => (
        <p key={warning} className={s.notice} role="status">
          {warning}
        </p>
      ))}
      {content}
      {group && (
        <ScheduleFreshness
          fetchedAt={schedule?.fetched_at || null}
          stale={schedule?.stale || false}
          pending={pending}
          onRefresh={onRefresh}
        />
      )}
      <div className={s.footer}>
        <span>Особые даты и условия — в записи занятия</span>
        <span>МСК · UTC+3</span>
      </div>
    </section>
  )
}
