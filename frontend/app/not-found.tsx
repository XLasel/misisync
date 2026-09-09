import s from './not-found.module.css'
import Link from 'next/link'
export default function NotFound() {
  return (
    <main className={s.root}>
      <div className={s.content}>
        <h1 className={s.title}>Страница не найдена</h1>
        <Link className={s.button} href="/">
          К расписанию
        </Link>
      </div>
    </main>
  )
}
