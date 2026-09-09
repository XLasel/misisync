import { ScheduleDashboard } from '@/widgets/schedule/ui/schedule-dashboard'
import { SiteHeader } from '@/widgets/site-header/ui/site-header'
import { moscowToday } from '@/shared/lib/calendar'
export const dynamic = 'force-dynamic'
export default function Home() {
  return (
    <>
      <SiteHeader sourceUrl="https://edu.misis.ru/schedule?filial=MOSCOW" />
      <ScheduleDashboard today={moscowToday()} />
    </>
  )
}
