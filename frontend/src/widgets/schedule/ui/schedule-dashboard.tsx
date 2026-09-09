'use client'
import { useCalendar } from '../model/use-calendar'
import { SchedulePanel } from './schedule-panel'
import { GroupPicker } from '../../../features/group-selection/ui/group-picker'

export function ScheduleDashboard({ today }: { today: string }) {
  const state = useCalendar(today)
  return (
    <main>
      <div className="heading">
        <div>
          <p className="eyebrow">ТВОЯ УЧЕБНАЯ НЕДЕЛЯ</p>
          <h1>
            Расписание<span>.</span>
          </h1>
        </div>
        <span className="heading-note">
          Предметы, время, аудитории.
          <br />
          Всё, что нужно перед парой.
        </span>
      </div>
      <div className="workspace">
        <aside>
          <GroupPicker
            groups={state.catalog}
            selected={state.group}
            onSelect={state.selectGroup}
            pending={state.catalogPending}
          />
          <p className="sidebar-note">
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
      <footer>
        <span>
          <strong>misisync</strong>
          <span className="footer-divider">/</span>Учёба в своём ритме
        </span>
        <span>Неофициальный студенческий сервис</span>
      </footer>
    </main>
  )
}
