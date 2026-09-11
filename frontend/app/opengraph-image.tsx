import { ImageResponse } from 'next/og'

export const alt = 'Misisync — расписание МИСИС. Учёба в своём ритме.'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'
export const dynamic = 'force-static'

// ImageResponse renders a PNG at build time; inline styles are required by its renderer.
export default function OpenGraphImage() {
  return new ImageResponse(
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        padding: '64px 72px',
        background: '#0c1018',
        color: '#e3e9f4',
        fontFamily: 'sans-serif',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 68,
            height: 68,
            borderRadius: 20,
            background: '#0541f0',
            fontSize: 46,
            fontWeight: 700,
          }}
        >
          M
        </div>
        <div style={{ display: 'flex', fontSize: 42, fontWeight: 700 }}>misisync</div>
        <div style={{ display: 'flex', marginLeft: 12, color: '#9bb2ff', fontSize: 22 }}>БЕТА</div>
      </div>
      <div
        style={{ display: 'flex', marginTop: 62, fontSize: 76, fontWeight: 700, letterSpacing: -3 }}
      >
        Расписание МИСИС.
      </div>
      <div style={{ display: 'flex', marginTop: 14, fontSize: 38, color: '#9eafff' }}>
        Учёба в своём ритме.
      </div>
      <div style={{ display: 'flex', gap: 16, marginTop: 40 }}>
        {['Твоя группа', 'Твоя неделя', 'Твои пары'].map((label) => (
          <div
            key={label}
            style={{
              display: 'flex',
              padding: '12px 22px',
              background: '#172334',
              borderRadius: 12,
              fontSize: 24,
            }}
          >
            {label}
          </div>
        ))}
      </div>
      <div
        style={{
          display: 'flex',
          marginTop: 'auto',
          justifyContent: 'space-between',
          fontSize: 20,
          color: '#9caac0',
        }}
      >
        <span>schedule.sovngarde.ru</span>
        <span>Неофициальный студенческий сервис</span>
      </div>
    </div>,
    size,
  )
}
