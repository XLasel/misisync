<script setup lang="ts">
type Lesson = { id: string; group_name: string; weekday: number; start_time: string; end_time: string; subject: string; lesson_type: string; teacher: string; room: string; subgroup: string; week_pattern: string; notes: string; raw_text: string }
type Status = { last_success: string | null; last_attempt: string | null; last_error: string | null; updating: boolean; group_count: number; lesson_count: number; source_url: string; warnings: string[] }
const group = ref('')
const search = ref('')
const weekday = ref(0)
const pattern = ref('all')
const days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
const shortDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
const { data: status, refresh: refreshStatus } = await useFetch<Status>('/api/status')
const { data: groups, error: groupsError, refresh: refreshGroups } = await useFetch<string[]>('/api/groups', { default: () => [] })
const options = computed(() => groups.value.filter(g => g.toLocaleLowerCase('ru').includes(search.value.toLocaleLowerCase('ru'))))
const { data: schedule, status: loadState, error: scheduleError, refresh: refreshSchedule } = await useFetch<Lesson[]>('/api/schedule', { query: { group }, default: () => [], immediate: false, watch: false })
watch(group, async value => {
  schedule.value = []
  if (import.meta.client) localStorage.setItem('misisync-group', value)
  if (value) await refreshSchedule()
})
const filtered = computed(() => schedule.value.filter(l => pattern.value === 'all' || l.week_pattern === 'all' || l.week_pattern === pattern.value))
const lessons = computed(() => filtered.value.filter(l => l.weekday === weekday.value))
const updated = computed(() => status.value?.last_success ? new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Europe/Moscow' }).format(new Date(status.value.last_success)) : null)
const kind = (l: Lesson) => /лек/i.test(l.lesson_type) ? 'lecture' : /лаб/i.test(l.lesson_type) ? 'lab' : 'practice'
const weekLabel = (v: string) => v === 'odd' ? 'Нечётная неделя' : v === 'even' ? 'Чётная неделя' : ''
let poll: ReturnType<typeof setInterval> | undefined
async function reload() { await Promise.all([refreshStatus(), refreshGroups()]); if (group.value) await refreshSchedule() }
onMounted(() => {
  const saved = localStorage.getItem('misisync-group') || ''
  if (groups.value.includes(saved)) group.value = saved
  weekday.value = (new Date(new Date().toLocaleString('en-US', { timeZone: 'Europe/Moscow' })).getDay() + 6) % 7
  poll = setInterval(reload, 60000)
})
onUnmounted(() => { if (poll) clearInterval(poll) })
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <a class="brand" href="/" aria-label="Misisync, главная"><img src="/favicon.svg" alt="" width="37" height="37"><span>misi<span class="brand-light">sync</span><sup>β</sup></span></a>
      <span class="header-context">Расписание МИСИС</span>
      <a class="source-link" href="https://misis.ru/students/schedule/" target="_blank" rel="noopener noreferrer">Сайт университета <span aria-hidden="true">↗</span></a>
    </header>
    <main>
      <div class="heading"><div><p class="eyebrow">УЧЁБА В СВОЁМ РИТМЕ</p><h1>Твоё расписание<span>.</span></h1><p class="intro">Все пары на день — в одном месте.</p></div><span class="semester">МИСИС <span> / </span> Учебные занятия</span></div>
      <div class="workspace">
        <aside>
          <section class="group-panel">
            <div class="panel-label"><span class="small-icon" aria-hidden="true">⌘</span><h2>Учебная группа</h2></div>
            <label for="group-search" class="field-label">Найти свою группу</label>
            <input id="group-search" v-model="search" placeholder="Например, БИВТ-24" autocomplete="off" type="search">
            <label for="group" class="sr-only">Выбрать группу</label>
            <select id="group" v-model="group"><option value="">Выберите группу</option><option v-for="g in options" :key="g" :value="g">{{ g }}</option></select>
            <p v-if="search && !options.length" class="muted">Групп с таким названием нет.</p>
            <p class="hint">Выбранная группа сохранится на этом устройстве.</p>
          </section>
          <section class="week-panel"><p class="field-label">Учебная неделя</p><label for="week" class="sr-only">Чётность недели</label><select id="week" v-model="pattern"><option value="all">Все недели</option><option value="odd">Нечётная неделя</option><option value="even">Чётная неделя</option></select><p class="hint">Условия и даты отдельных занятий указаны в карточках.</p></section>
          <section class="sync-panel"><div class="sync-title"><span class="status-dot" :class="{ warning: status?.last_error || !updated }"></span>{{ status?.updating ? 'Обновляем расписание' : updated ? 'Данные загружены' : 'Ожидаем расписание' }}</div><template v-if="updated"><p>Последнее успешное обновление</p><time :datetime="status?.last_success || undefined">{{ updated }} МСК</time></template><p v-else>После первой загрузки здесь появится время обновления.</p><p v-if="status?.last_error" class="sync-error">Источник временно недоступен или изменился. {{ updated ? 'Показываем последнюю успешную версию.' : 'Повторим загрузку автоматически.' }}</p><a :href="status?.source_url || 'https://misis.ru/students/'" target="_blank" rel="noopener noreferrer">Официальный источник ↗</a></section>
        </aside>
        <section class="schedule-panel" aria-label="Расписание занятий">
          <div class="schedule-heading"><div><span class="overline">РАСПИСАНИЕ ЗАНЯТИЙ</span><h2>{{ group || 'Твоя учебная неделя' }}</h2></div><span class="group-badge">{{ group ? 'По дням' : 'Выбери группу слева' }}</span></div>
          <nav class="day-tabs" aria-label="Дни недели"><button v-for="(day, i) in days" :key="day" :aria-pressed="weekday === i" :class="{ active: weekday === i }" @click="weekday = i"><span>{{ shortDays[i] }}</span><span class="day-count">{{ group ? filtered.filter(l => l.weekday === i).length : '—' }}</span></button></nav>
          <div class="day-heading"><h3>{{ days[weekday] }}</h3><span v-if="group && loadState !== 'pending'">Занятий: {{ lessons.length }}</span><span v-else>Время московское</span></div>
          <div v-if="groupsError || (group && scheduleError)" class="empty-state" role="alert"><span class="empty-symbol">↻</span><h3>Не удалось получить расписание</h3><p>Проверь подключение и попробуй ещё раз.</p><button class="retry" @click="reload">Повторить</button></div>
          <div v-else-if="!group" class="empty-state"><span class="empty-symbol" aria-hidden="true">▦</span><h3>Начнём с твоей группы</h3><p>{{ groups.length ? 'Найди её по названию — и здесь появятся предметы, преподаватели и аудитории.' : 'Первое расписание ещё загружается. Список групп появится автоматически.' }}</p></div>
          <div v-else-if="loadState === 'pending'" class="empty-state" role="status"><span class="empty-symbol">⋯</span><h3>Загружаем занятия</h3></div>
          <div v-else-if="!lessons.length" class="empty-state"><span class="empty-symbol" aria-hidden="true">☀</span><h3>В расписании нет занятий</h3><p>Для этого дня и выбранной недели пары не указаны в источнике.</p></div>
          <ol v-else class="lessons">
            <li v-for="lesson in lessons" :key="lesson.id" class="lesson-row"><div class="time-column"><strong>{{ lesson.start_time }}</strong><span>{{ lesson.end_time }}</span></div><article class="lesson-card" :class="kind(lesson)"><div class="lesson-top"><span class="type-label">{{ lesson.lesson_type || 'Занятие' }}</span><span v-if="lesson.subgroup" class="subgroup">{{ lesson.subgroup }}</span><span v-if="lesson.week_pattern !== 'all'" class="week-tag">{{ weekLabel(lesson.week_pattern) }}</span></div><h4>{{ lesson.subject }}</h4><div v-if="lesson.teacher || lesson.room" class="lesson-meta"><span v-if="lesson.teacher">{{ lesson.teacher }}</span><span v-if="lesson.room" class="room">⌖ {{ lesson.room }}</span></div><p v-if="lesson.notes" class="lesson-notes">{{ lesson.notes }}</p><details><summary>Запись в источнике</summary><p>{{ lesson.raw_text }}</p></details></article></li>
          </ol>
          <p v-if="status?.warnings?.length" class="data-notice">В источнике есть дополнительные примечания. Проверяй условия занятий в карточках и исходной таблице.</p>
          <div class="schedule-bottom"><span class="legend"><i class="lecture-dot"></i>Лекции <i class="practice-dot"></i>Практика <i class="lab-dot"></i>Лабораторные</span><span>Время МСК, UTC+3</span></div>
        </section>
      </div>
      <footer><span><strong>misisync</strong> <span class="footer-divider">/</span> Меньше поисков. Больше времени.</span><span>Неофициальный студенческий сервис</span></footer>
    </main>
  </div>
</template>
