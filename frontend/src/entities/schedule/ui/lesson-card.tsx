import s from './lesson-card.module.css'
import type { Lesson } from '../model/types'
const kind = (lesson: Lesson) =>
  /лек/i.test(lesson.lesson_type)
    ? 'lecture'
    : /лаб/i.test(lesson.lesson_type)
      ? 'lab'
      : /прак|семин|^пр\.?$/i.test(lesson.lesson_type)
        ? 'practice'
        : 'other'
export function LessonCard({ lesson }: { lesson: Lesson }) {
  const type = kind(lesson)
  const label = {
    lecture: 'Лекция',
    practice: 'Практика',
    lab: 'Лабораторная',
    other: lesson.lesson_type || 'Занятие',
  }[type]
  const subgroup = lesson.subgroup_ids.length
    ? `Подгрупп${lesson.subgroup_ids.length === 1 ? 'а' : 'ы'} ${lesson.subgroup_ids.join(', ')}`
    : lesson.subgroup_label.trim()
  return (
    <li className={s.root}>
      <div className={s.time}>
        <strong>{lesson.start_time || '—'}</strong>
        <span>{lesson.end_time || 'Время не указано'}</span>
      </div>
      <article className={`${s.card} ${s[type]}`}>
        <div className={s.header}>
          <span className={s.type}>
            <i />
            {label}
          </span>
          {subgroup && <span className={s.subgroup}>{subgroup}</span>}
        </div>
        <h4>{lesson.subject}</h4>
        {(lesson.teachers.length > 0 || lesson.rooms.length > 0) && (
          <div className={s.meta}>
            {lesson.teachers.length > 0 && <span>{lesson.teachers.join(', ')}</span>}
            {lesson.rooms.length > 0 && (
              <span className={s.room}>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z" />
                  <circle cx="12" cy="10" r="2" />
                </svg>
                {lesson.rooms.join(', ')}
              </span>
            )}
          </div>
        )}
        {[...lesson.notes, ...lesson.warnings].map((note, i) => (
          <p key={i} className={s.notes}>
            {note}
          </p>
        ))}
        <details className={s.source}>
          <summary>Запись в источнике</summary>
          {lesson.evidence.map((original, i) => (
            <div key={i} className={s.record}>
              <p>{original.raw_text}</p>
              <span>{original.label}</span>
            </div>
          ))}
        </details>
      </article>
    </li>
  )
}
