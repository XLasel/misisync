export default defineNuxtConfig({
  compatibilityDate: '2026-09-08',
  srcDir: '.',
  devtools: { enabled: false },
  css: ['~/assets/main.css'],
  runtimeConfig: { apiBase: 'http://127.0.0.1:8000', scheduleRateLimitPerMinute: 60, trustProxy: false },
  routeRules: {
    '/**': {
      headers: {
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
        'Cross-Origin-Opener-Policy': 'same-origin',
      },
    },
  },
  app: { head: {
    htmlAttrs: { lang: 'ru', style: 'color-scheme: dark; background-color: #0c1018' },
    title: 'Misisync — расписание МИСИС',
    meta: [{ name: 'description', content: 'Расписание занятий МИСИС по группам, дням и подгруппам. Данные из официальных источников университета.' }, { name: 'theme-color', content: '#0c1018' }],
    link: [{ rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }]
  } }
})
