'use client'
import { useId, useRef, useState } from 'react'
import type { Group } from '../../../entities/schedule/model/types'
import { normalizeGroupSearch } from '../../../shared/lib/search'

type Props = {
  groups: Group[]
  selected: Group | null
  onSelect: (id: string) => void
  pending: boolean
}
export function GroupPicker({ groups, selected, onSelect, pending }: Props) {
  const [query, setQuery] = useState('')
  const [institute, setInstitute] = useState('')
  const [level, setLevel] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const input = useRef<HTMLInputElement>(null)
  const id = useId()
  const institutes = [...new Set(groups.flatMap((g) => g.institutes))].sort((a, b) =>
    a.localeCompare(b, 'ru'),
  )
  const levels = [...new Set(groups.map((g) => g.education_level).filter(Boolean))]
  const matches = groups.filter(
    (g) =>
      normalizeGroupSearch(g.name).includes(normalizeGroupSearch(query)) &&
      (!institute || g.institutes.includes(institute)) &&
      (!level || g.education_level === level),
  )
  const options = matches.slice(0, 60)
  function choose(group: Group) {
    onSelect(group.id)
    setQuery('')
    setOpen(false)
  }
  function move(direction: number) {
    setOpen(true)
    const next = Math.max(0, Math.min(options.length - 1, active + direction))
    setActive(next)
    document.getElementById(`${id}-option-${next}`)?.scrollIntoView({ block: 'nearest' })
  }
  return (
    <section className="group-panel">
      <div className="panel-label">
        <span className="section-number">01</span>
        <h2>Твоя группа</h2>
      </div>
      <div
        className="group-picker"
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false)
        }}
      >
        <label htmlFor="group-search" className="sr-only">
          Найти учебную группу
        </label>
        <div className="search-field">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="10.5" cy="10.5" r="6.5" />
            <path d="m16 16 4 4" />
          </svg>
          <input
            id="group-search"
            ref={input}
            value={query}
            type="text"
            role="combobox"
            placeholder={selected ? 'Найти другую группу' : 'Например, БИВТ-26'}
            autoComplete="off"
            aria-autocomplete="list"
            aria-controls={`${id}-results`}
            aria-expanded={open}
            aria-activedescendant={open && options[active] ? `${id}-option-${active}` : undefined}
            onChange={(event) => {
              setQuery(event.target.value)
              setActive(0)
              setOpen(true)
            }}
            onFocus={() => {
              setOpen(true)
              setActive(0)
            }}
            onClick={() => setOpen(true)}
            onKeyDown={(event) => {
              if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                event.preventDefault()
                move(event.key === 'ArrowDown' ? 1 : -1)
              }
              if (event.key === 'Enter' && open && options[active]) {
                event.preventDefault()
                choose(options[active]!)
              }
              if (event.key === 'Escape') setOpen(false)
            }}
          />
        </div>
        {open && (
          <div className="picker-popover">
            <div className="results-caption" role="status">
              {pending
                ? 'Загружаем группы…'
                : matches.length
                  ? `Найдено групп: ${matches.length}`
                  : 'Ничего не найдено'}
            </div>
            <ul
              id={`${id}-results`}
              role="listbox"
              aria-label="Учебные группы"
              className="group-results"
            >
              {options.map((item, i) => (
                <li
                  id={`${id}-option-${i}`}
                  key={item.id}
                  role="option"
                  aria-label={`${item.name} ${item.education_level || 'Уровень не указан'}`}
                  aria-selected={item.id === selected?.id}
                  className={i === active ? 'highlighted' : ''}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => choose(item)}
                >
                  <strong>{item.name}</strong>
                  <span>{item.education_level || 'Уровень не указан'}</span>
                </li>
              ))}
            </ul>
            {!pending && !matches.length && (
              <p className="search-help">Попробуй часть названия или сбрось уточнения.</p>
            )}
            {matches.length > options.length && (
              <p className="search-help">Показаны первые 60. Введи название группы.</p>
            )}
          </div>
        )}
      </div>
      {(institutes.length > 0 || levels.length > 0) && (
        <details className="search-refinements">
          <summary>
            Уточнить поиск{' '}
            {(institute || level) && (
              <span className="filter-count">{Number(!!institute) + Number(!!level)}</span>
            )}
          </summary>
          <div className="refinements-content">
            {institutes.length > 0 && (
              <>
                <label htmlFor={`${id}-institute`}>Институт</label>
                <select
                  id={`${id}-institute`}
                  value={institute}
                  onChange={(e) => {
                    setInstitute(e.target.value)
                    setActive(0)
                  }}
                >
                  <option value="">Все институты</option>
                  {institutes.map((name) => (
                    <option key={name}>{name}</option>
                  ))}
                </select>
              </>
            )}
            {levels.length > 0 && (
              <>
                <label htmlFor={`${id}-level`}>Уровень образования</label>
                <select
                  id={`${id}-level`}
                  value={level}
                  onChange={(e) => {
                    setLevel(e.target.value)
                    setActive(0)
                  }}
                >
                  <option value="">Все уровни</option>
                  {levels.map((name) => (
                    <option key={name}>{name}</option>
                  ))}
                </select>
              </>
            )}
            {(institute || level) && (
              <button
                className="text-button"
                onClick={() => {
                  setInstitute('')
                  setLevel('')
                  setQuery('')
                  input.current?.focus()
                }}
              >
                Сбросить уточнения
              </button>
            )}
          </div>
        </details>
      )}
      {selected ? (
        <div className="selected-group">
          <span className="overline">ВЫБРАННАЯ ГРУППА</span>
          <strong>{selected.name}</strong>
          <span>{selected.education_level}</span>
          {selected.institutes.map((name) => (
            <p key={name}>{name}</p>
          ))}
        </div>
      ) : (
        <p className="hint">Начни вводить название. Институт и уровень можно не выбирать.</p>
      )}
    </section>
  )
}
