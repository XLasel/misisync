export default defineNuxtConfig({
  compatibilityDate: '2026-09-08',
  srcDir: '.',
  devtools: { enabled: false },
  css: ['~/assets/main.css'],
  runtimeConfig: { apiBase: 'http://127.0.0.1:8000' },
  app: { head: {
    htmlAttrs: { lang: 'ru' },
    title: 'Misisync — расписание МИСИС',
    meta: [{ name: 'description', content: 'Расписание занятий МИСИС по группам, дням и подгруппам. Актуальные данные из официальных таблиц университета.' }, { name: 'theme-color', content: '#0541f0' }],
    link: [{ rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }]
  } }
})
