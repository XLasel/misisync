import Image from 'next/image'
import Link from 'next/link'

import s from './site-header.module.css'

export function SiteHeader({ sourceUrl }: { sourceUrl: string }) {
  return (
    <header className={s.root}>
      <Link className={s.brand} href="/" aria-label="Misisync, главная">
        <Image src="/favicon.svg" alt="" width={37} height={37} />
        <span>
          misi<span className={s.brandLight}>sync</span>
          <sup>β</sup>
        </span>
      </Link>
      <span className={s.context}>Расписание МИСИС</span>
      <a className={s.source} href={sourceUrl} target="_blank" rel="noopener noreferrer">
        Источник <span aria-hidden="true">↗</span>
      </a>
    </header>
  )
}
