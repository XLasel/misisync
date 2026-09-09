import s from './empty-state.module.css'
import type { ReactNode } from 'react'
export function EmptyState({
  symbol,
  title,
  children,
  alert = false,
}: {
  symbol: string
  title: string
  children?: ReactNode
  alert?: boolean
}) {
  return (
    <div className={s.root} role={alert ? 'alert' : 'status'}>
      <span className={s.symbol} aria-hidden="true">
        {symbol}
      </span>
      <h3>{title}</h3>
      {children}
    </div>
  )
}
