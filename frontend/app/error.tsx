'use client'

import { Button, StatusPage } from '@/shared/ui'

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <StatusPage title="Не удалось открыть расписание" alert>
      <p>Попробуй загрузить страницу ещё раз.</p>
      <Button onClick={reset}>Повторить</Button>
    </StatusPage>
  )
}
