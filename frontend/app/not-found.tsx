import { ButtonLink } from '@/shared/ui/button'
import { StatusPage } from '@/shared/ui/status-page'

export default function NotFound() {
  return (
    <StatusPage title="Страница не найдена">
      <ButtonLink href="/">К расписанию</ButtonLink>
    </StatusPage>
  )
}
