'use client'
import s from './error-page.module.css'
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className={s.root}>
      <div className={s.content} role="alert">
        <h1 className={s.title}>Не удалось открыть расписание</h1>
        <p>Попробуй загрузить страницу ещё раз.</p>
        <button className={s.button} onClick={reset}>
          Повторить
        </button>
      </div>
    </main>
  )
}
