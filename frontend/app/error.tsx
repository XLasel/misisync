'use client'
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main>
      <div className="empty-state" role="alert">
        <h1>Не удалось открыть расписание</h1>
        <p>Попробуй загрузить страницу ещё раз.</p>
        <button className="primary-button" onClick={reset}>
          Повторить
        </button>
      </div>
    </main>
  )
}
