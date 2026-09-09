import type { Metadata, Viewport } from 'next'
import type { ReactNode } from 'react'

import '@/shared/styles/tokens.css'
import './globals.css'

export const metadata: Metadata = {
  title: 'Misisync — расписание МИСИС',
  description:
    'Расписание занятий МИСИС по группам, дням и подгруппам. Данные из официального API университета.',
  icons: { icon: '/favicon.svg' },
}
export const viewport: Viewport = { themeColor: '#0c1018', colorScheme: 'dark' }
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  )
}
