import type { ReactNode } from 'react'

import s from './empty-state.module.css'

export function EmptyState({
  symbol,
  title,
  children,
  alert = false,
  titleAs: Title = 'h3',
}: {
  symbol?: string
  title: string
  children?: ReactNode
  alert?: boolean
  titleAs?: 'h1' | 'h2' | 'h3'
}) {
  return (
    <div className={s.root} role={alert ? 'alert' : 'status'}>
      {symbol && (
        <span className={s.symbol} aria-hidden="true">
          {symbol}
        </span>
      )}
      <Title className={s.title}>{title}</Title>
      {children}
    </div>
  )
}
