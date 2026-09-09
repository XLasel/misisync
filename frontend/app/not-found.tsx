import { ButtonLink, StatusPage } from '@/shared/ui'

export default function NotFound() {
  return (
    <StatusPage title="Страница не найдена">
      <ButtonLink href="/">К расписанию</ButtonLink>
    </StatusPage>
  )
}
