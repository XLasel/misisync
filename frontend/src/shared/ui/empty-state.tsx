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
    <div className="empty-state" role={alert ? 'alert' : 'status'}>
      <span className="empty-symbol" aria-hidden="true">
        {symbol}
      </span>
      <h3>{title}</h3>
      {children}
    </div>
  )
}
