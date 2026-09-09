import Link from 'next/link'
import Image from 'next/image'
export function SiteHeader({ sourceUrl }: { sourceUrl: string }) {
  return (
    <header className="topbar">
      <Link className="brand" href="/" aria-label="Misisync, главная">
        <Image src="/favicon.svg" alt="" width={37} height={37} />
        <span>
          misi<span className="brand-light">sync</span>
          <sup>β</sup>
        </span>
      </Link>
      <span className="header-context">Расписание МИСИС</span>
      <a className="source-link" href={sourceUrl} target="_blank" rel="noopener noreferrer">
        Источник <span aria-hidden="true">↗</span>
      </a>
    </header>
  )
}
