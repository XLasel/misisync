'use client'

import { GroupPicker } from '@/features/group-selection/ui/group-picker'

import { useCalendar } from '../model/use-calendar'

import { SchedulePanel } from './schedule-panel'

import s from './schedule-dashboard.module.css'

export function ScheduleDashboard({ today }: { today: string }) {
  const state = useCalendar(today)
  return (
    <main className={s.root}>
      <div className={s.heading}>
        <div>
          <p className={s.eyebrow}>ТВОЯ УЧЕБНАЯ НЕДЕЛЯ</p>
          <h1 className={s.title}>
            Расписание<span>.</span>
          </h1>
        </div>
        <span className={s.description}>
          Предметы, время, аудитории.
          <br />
          Всё, что нужно перед парой.
        </span>
      </div>
      <div className={s.workspace}>
        <aside className={s.sidebar}>
          <GroupPicker
            groups={state.catalog}
            selected={state.group}
            onSelect={state.selectGroup}
            pending={state.catalogPending}
          />
          <p className={s.note}>
            Группа и подгруппа сохраняются
            <br />
            на этом устройстве.
          </p>
        </aside>
        <SchedulePanel
          group={state.group}
          schedule={state.schedule}
          dates={state.dates}
          weekday={state.weekday}
          subgroup={state.subgroup}
          pending={state.pending}
          catalogPending={state.catalogPending}
          error={state.catalogError || state.error}
          onWeek={state.setWeekStart}
          onDay={state.setWeekday}
          onSubgroup={state.selectSubgroup}
          onRefresh={state.reload}
        />
      </div>
      <footer className={s.footer}>
        <span>
          <strong>misisync</strong>
          <span className={s.divider}>/</span>Учёба в своём ритме
        </span>
        <span>Неофициальный студенческий сервис</span>
      </footer>
    </main>
  )
}
