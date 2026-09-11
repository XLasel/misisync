import type { Metadata, Viewport } from 'next'
import type { ReactNode } from 'react'

import { site } from '@/shared/config/site'

import '@/shared/styles/tokens.css'
import './globals.css'

export const metadata: Metadata = {
  metadataBase: new URL(site.url),
  applicationName: site.name,
  title: site.title,
  description: site.description,
  alternates: { canonical: '/' },
  openGraph: {
    type: 'website',
    locale: 'ru_RU',
    url: '/',
    siteName: site.name,
    title: site.title,
    description: site.description,
    images: [{ url: '/opengraph-image', width: 1200, height: 630, alt: site.title }],
  },
  twitter: {
    card: 'summary_large_image',
    title: site.title,
    description: site.description,
    images: ['/opengraph-image'],
  },
  robots: { index: true, follow: true },
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
