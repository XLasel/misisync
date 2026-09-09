import type { ReactNode } from 'react'

import { EmptyState } from './empty-state'

import s from './status-page.module.css'

export function StatusPage({
  title,
  children,
  alert = false,
}: {
  title: string
  children?: ReactNode
  alert?: boolean
}) {
  return (
    <main className={s.root}>
      <EmptyState title={title} titleAs="h1" alert={alert}>
        {children}
      </EmptyState>
    </main>
  )
}
