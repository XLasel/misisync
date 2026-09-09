import Link from 'next/link'
export default function NotFound() {
  return (
    <main>
      <div className="empty-state">
        <h1>Страница не найдена</h1>
        <Link className="primary-button" href="/">
          К расписанию
        </Link>
      </div>
    </main>
  )
}
