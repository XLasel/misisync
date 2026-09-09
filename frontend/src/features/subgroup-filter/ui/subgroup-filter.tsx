export function SubgroupFilter({
  values,
  selected,
  onChange,
}: {
  values: number[]
  selected: string
  onChange: (value: string) => void
}) {
  if (!values.length) return null
  return (
    <div className="subgroup-control" role="group" aria-label="Фильтр по подгруппе">
      <span>Подгруппа</span>
      <div className="segmented">
        <button
          aria-pressed={selected === 'all'}
          className={selected === 'all' ? 'active' : ''}
          onClick={() => onChange('all')}
        >
          Все
        </button>
        {values.map((id) => (
          <button
            key={id}
            aria-label={`Подгруппа ${id}`}
            aria-pressed={selected === String(id)}
            className={selected === String(id) ? 'active' : ''}
            onClick={() => onChange(String(id))}
          >
            {id}
          </button>
        ))}
      </div>
    </div>
  )
}
