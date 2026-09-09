'use client'

import { Button } from '@/shared/ui/button'
import { StatusPage } from '@/shared/ui/status-page'

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <StatusPage title="Не удалось открыть расписание" alert>
      <p>Попробуй загрузить страницу ещё раз.</p>
      <Button onClick={reset}>Повторить</Button>
    </StatusPage>
  )
}
