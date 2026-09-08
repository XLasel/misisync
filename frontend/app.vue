<script setup lang="ts">
import { normalizeGroupSearch, scheduleCards } from '~/utils/schedule'
import type { Lesson } from '~/utils/schedule'
type Group = { name: string; institutes: string[]; education_level: string }
type SyncStatus = { last_success: string | null; last_error: string | null; updating: boolean; source_url: string; warnings: string[] }
const days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
const shortDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
const group = ref('')
const query = ref('')
const institute = ref('')
const level = ref('')
const weekday = ref(0)
const week = ref('all')
const subgroup = ref('all')
const pickerOpen = ref(false)
const activeOption = ref(0)
const searchInput = ref<HTMLInputElement>()
const { data: sync, refresh: refreshStatus } = await useFetch<SyncStatus>('/api/status')
const { data: catalog, error: catalogError, refresh: refreshCatalog } = await useFetch<Group[]>('/api/catalog', { default: () => [] })
const { data: schedule, status: loading, error: scheduleError, refresh: refreshSchedule } = await useFetch<Lesson[]>('/api/schedule', {
  query: { group }, default: () => [], immediate: false, watch: false,
})
const institutes = computed(() => [...new Set(catalog.value.flatMap(g => g.institutes))].sort((a, b) => a.localeCompare(b, 'ru')))
const levels = computed(() => [...new Set(catalog.value.map(g => g.education_level).filter(Boolean))])
const matches = computed(() => catalog.value.filter(g =>
  normalizeGroupSearch(g.name).includes(normalizeGroupSearch(query.value)) &&
  (!institute.value || g.institutes.includes(institute.value)) && (!level.value || g.education_level === level.value)))
const options = computed(() => matches.value.slice(0, 60))
const selectedGroup = computed(() => catalog.value.find(g => g.name === group.value))
const subgroups = computed(() => [...new Set(schedule.value.flatMap(l => l.subgroup_ids || []))].sort((a, b) => a - b))
const cards = computed(() => scheduleCards(schedule.value, week.value, subgroup.value))
const lessons = computed(() => cards.value.filter(l => l.weekday === weekday.value))
const lastUpdated = computed(() => sync.value?.last_success ? new Intl.DateTimeFormat('ru-RU', {
  day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Moscow',
}).format(new Date(sync.value.last_success)) : null)
const kind = (lesson: Lesson) => /лек/i.test(lesson.lesson_type) ? 'lecture' : /лаб/i.test(lesson.lesson_type) ? 'lab' : /прак|семин|^пр\.?$/i.test(lesson.lesson_type) ? 'practice' : 'other'
const kindLabel = (lesson: Lesson) => ({ lecture: 'Лекция', practice: 'Практика', lab: 'Лабораторная', other: lesson.lesson_type || 'Занятие' })[kind(lesson)]
const subgroupLabel = (lesson: Lesson) => lesson.subgroup_ids.length ? `Подгрупп${lesson.subgroup_ids.length === 1 ? 'а' : 'ы'} ${lesson.subgroup_ids.join(', ')}` : lesson.subgroup || 'Подгруппа не указана'
const weekLabel = (value: string) => value === 'odd' ? 'Нечётная неделя' : value === 'even' ? 'Чётная неделя' : ''
function selectGroup(value: string) { group.value = value; query.value = ''; pickerOpen.value = false }
function openPicker() { pickerOpen.value = true; activeOption.value = 0 }
function moveOption(direction: number) {
  if (!pickerOpen.value) { openPicker(); return }
  activeOption.value = Math.max(0, Math.min(options.value.length - 1, activeOption.value + direction))
  nextTick(() => document.getElementById(`group-option-${activeOption.value}`)?.scrollIntoView({ block: 'nearest' }))
}
function chooseActive() {
  if (pickerOpen.value && options.value[activeOption.value]) selectGroup(options.value[activeOption.value]!.name)
}
function closePicker(event: FocusEvent) {
  if (!(event.currentTarget as HTMLElement).contains(event.relatedTarget as Node | null)) pickerOpen.value = false
}
function resetSearch() { institute.value = ''; level.value = ''; query.value = ''; openPicker(); searchInput.value?.focus() }
watch([query, institute, level], () => { activeOption.value = 0 })
watch(group, async value => {
  schedule.value = []
  if (import.meta.client) {
    localStorage.setItem('misisync-group', value)
    subgroup.value = localStorage.getItem(`misisync-subgroup:${value}`) || 'all'
  }
  if (value) await refreshSchedule()
})
watch([subgroups, loading], ([values, state]) => {
  if (state === 'success' && subgroup.value !== 'all' && !values.includes(Number(subgroup.value))) subgroup.value = 'all'
})
watch(subgroup, value => {
  if (import.meta.client && group.value) localStorage.setItem(`misisync-subgroup:${group.value}`, value)
})
async function reload() { await Promise.all([refreshStatus(), refreshCatalog()]); if (group.value) await refreshSchedule() }
let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  const saved = localStorage.getItem('misisync-group') || ''
  if (catalog.value.some(g => g.name === saved)) selectGroup(saved)
  weekday.value = (new Date(new Date().toLocaleString('en-US', { timeZone: 'Europe/Moscow' })).getDay() + 6) % 7
  timer = setInterval(reload, 60000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <a class="brand" href="/" aria-label="Misisync, главная"><img src="/favicon.svg" alt="" width="37" height="37"><span>misi<span class="brand-light">sync</span><sup>β</sup></span></a>
      <span class="header-context">Расписание МИСИС</span>
      <a class="source-link" href="https://misis.ru/students/schedule/" target="_blank" rel="noopener noreferrer">Источник <span aria-hidden="true">↗</span></a>
    </header>
    <main>
      <div class="heading"><div><p class="eyebrow">ТВОЯ УЧЕБНАЯ НЕДЕЛЯ</p><h1>Расписание<span>.</span></h1></div><span class="heading-note">Предметы, время, аудитории.<br>Всё, что нужно перед парой.</span></div>
      <div class="workspace">
        <aside>
          <section class="group-panel">
            <div class="panel-label"><span class="section-number">01</span><h2>Твоя группа</h2></div>
            <div class="group-picker" @focusout="closePicker">
              <label for="group-search" class="sr-only">Найти учебную группу</label>
              <div class="search-field"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/></svg>
                <input id="group-search" ref="searchInput" v-model="query" type="text" role="combobox"
                  :placeholder="group ? 'Найти другую группу' : 'Например, БИВТ-26'" autocomplete="off"
                  aria-autocomplete="list" aria-controls="group-results" :aria-expanded="pickerOpen"
                  :aria-activedescendant="pickerOpen && options.length ? `group-option-${activeOption}` : undefined"
                  @focus="openPicker" @click="openPicker" @input="openPicker" @keydown.down.prevent="moveOption(1)" @keydown.up.prevent="moveOption(-1)"
                  @keydown.enter.prevent="chooseActive" @keydown.esc.prevent="pickerOpen = false">
              </div>
              <div v-if="pickerOpen" class="picker-popover">
                <div class="results-caption">{{ matches.length ? `Найдено групп: ${matches.length}` : 'Ничего не найдено' }}</div>
                <ul id="group-results" role="listbox" aria-label="Учебные группы" class="group-results">
                  <li v-for="(item, i) in options" :id="`group-option-${i}`" :key="item.name" role="option" :aria-selected="item.name === group" :class="{ highlighted: i === activeOption }" @mousedown.prevent @click="selectGroup(item.name)"><strong>{{ item.name }}</strong><span>{{ item.education_level || 'Уровень не указан' }}</span></li>
                </ul>
                <p v-if="!matches.length" class="search-help">Попробуй часть названия или сбрось уточнения.</p>
                <p v-if="matches.length > options.length" class="search-help">Показаны первые 60. Введи название группы.</p>
              </div>
            </div>
            <details class="search-refinements"><summary>Уточнить поиск <span v-if="institute || level" class="filter-count">{{ Number(!!institute) + Number(!!level) }}</span></summary>
              <div class="refinements-content">
                <label for="institute">Институт</label><select id="institute" v-model="institute"><option value="">Все институты</option><option v-for="name in institutes" :key="name" :value="name">{{ name }}</option></select>
                <label for="level">Уровень образования</label><select id="level" v-model="level"><option value="">Все уровни</option><option v-for="name in levels" :key="name" :value="name">{{ name }}</option></select>
                <button v-if="institute || level" class="text-button" @click="resetSearch">Сбросить уточнения</button>
              </div>
            </details>
            <div v-if="selectedGroup" class="selected-group"><span class="overline">ВЫБРАННАЯ ГРУППА</span><strong>{{ selectedGroup.name }}</strong><span>{{ selectedGroup.education_level }}</span><p v-for="name in selectedGroup.institutes" :key="name">{{ name }}</p></div>
            <p v-else class="hint">Начни вводить название. Институт и уровень можно не выбирать.</p>
          </section>
          <section class="sync-panel" aria-label="Обновление данных">
            <div class="sync-title"><span class="status-dot" :class="{ warning: sync?.last_error || !lastUpdated }"></span>{{ sync?.updating ? 'Обновляем расписание' : lastUpdated ? 'Синхронизировано' : 'Ожидаем расписание' }}</div>
            <template v-if="lastUpdated"><p>Последняя успешная загрузка</p><time :datetime="sync?.last_success || undefined">{{ lastUpdated }} МСК</time></template><p v-else>Список групп появится после первой загрузки.</p>
            <p v-if="sync?.last_error" class="sync-error">Не удалось обновить источник. {{ lastUpdated ? 'Показываем последнюю успешную версию.' : 'Повторим попытку автоматически.' }}</p>
            <a :href="sync?.source_url || 'https://misis.ru/students/'" target="_blank" rel="noopener noreferrer">Официальный источник ↗</a>
          </section>
          <p class="sidebar-note">Группа и подгруппа сохраняются<br>на этом устройстве.</p>
        </aside>
        <section class="schedule-panel" aria-label="Расписание занятий">
          <div class="schedule-heading"><div><span class="overline">РАСПИСАНИЕ ЗАНЯТИЙ</span><h2>{{ group || 'Твоя учебная неделя' }}</h2></div><span class="template-badge">Недельный шаблон</span></div>
          <div v-if="group" class="schedule-controls">
            <div class="week-control"><label for="week">Неделя</label><select id="week" v-model="week"><option value="all">Все недели</option><option value="odd">Нечётная</option><option value="even">Чётная</option></select></div>
            <div v-if="subgroups.length" class="subgroup-control" aria-label="Фильтр по подгруппе"><span>Подгруппа</span><div class="segmented"><button :aria-pressed="subgroup === 'all'" :class="{ active: subgroup === 'all' }" @click="subgroup = 'all'">Все</button><button v-for="id in subgroups" :key="id" :aria-label="`Подгруппа ${id}`" :aria-pressed="subgroup === String(id)" :class="{ active: subgroup === String(id) }" @click="subgroup = String(id)">{{ id }}</button></div></div>
            <span v-else-if="loading === 'success'" class="no-subgroups">Подгруппы в источнике не указаны</span>
          </div>
          <nav class="day-tabs" aria-label="Дни недели"><button v-for="(day, i) in days" :key="day" :aria-label="day" :aria-pressed="weekday === i" :class="{ active: weekday === i }" @click="weekday = i"><span>{{ shortDays[i] }}</span><span class="day-count">{{ group ? cards.filter(l => l.weekday === i).length : '—' }}</span></button></nav>
          <div class="day-heading"><h3>{{ days[weekday] }}</h3><span>{{ group && loading !== 'pending' ? `Занятий: ${lessons.length}` : 'Время московское' }}</span></div>
          <p v-if="subgroup !== 'all' && group" class="filter-note">Подгруппа {{ subgroup }} + общие занятия. Записи без уточнения подгруппы тоже показаны.</p>
          <div v-if="catalogError || (group && scheduleError)" class="empty-state" role="alert"><span class="empty-symbol">↻</span><h3>Не удалось получить расписание</h3><p>Проверь подключение и попробуй ещё раз.</p><button class="primary-button" @click="reload">Повторить</button></div>
          <div v-else-if="!group" class="empty-state"><span class="empty-symbol" aria-hidden="true">▦</span><h3>Какая у тебя группа?</h3><p>{{ catalog.length ? 'Найди её по названию. Мы покажем пары и запомним твой выбор.' : 'Первое расписание ещё загружается. Список групп появится автоматически.' }}</p><button v-if="catalog.length" class="primary-button" @click="searchInput?.focus()">Найти группу <span aria-hidden="true">↗</span></button></div>
          <div v-else-if="loading === 'pending'" class="empty-state" role="status"><span class="empty-symbol">⋯</span><h3>Загружаем занятия</h3></div>
          <div v-else-if="!lessons.length" class="empty-state"><span class="empty-symbol" aria-hidden="true">☀</span><h3>В расписании нет занятий</h3><p>Для этого дня, недели и подгруппы пары не указаны в источнике.</p></div>
          <ol v-else class="lessons">
            <li v-for="lesson in lessons" :key="lesson.id" class="lesson-row"><div class="time-column"><strong>{{ lesson.start_time }}</strong><span>{{ lesson.end_time }}</span></div>
              <article class="lesson-card" :class="kind(lesson)">
                <div class="lesson-top"><span class="type-label"><i></i>{{ kindLabel(lesson) }}</span><span class="subgroup-tag">{{ subgroupLabel(lesson) }}</span><span v-if="lesson.week_pattern !== 'all'" class="week-tag">{{ weekLabel(lesson.week_pattern) }}</span></div>
                <h4>{{ lesson.subject }}</h4>
                <div v-if="lesson.teacher || lesson.room" class="lesson-meta"><span v-if="lesson.teacher">{{ lesson.teacher }}</span><span v-if="lesson.room" class="room"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2"/></svg>{{ lesson.room }}</span></div>
                <p v-if="lesson.notes" class="lesson-notes">{{ lesson.notes }}</p>
                <details class="source-details"><summary>Запись в источнике</summary><div v-for="original in lesson.originals" :key="original.id" class="source-record"><p>{{ original.raw_text }}</p><span>{{ original.source_sheet }} · {{ original.source_cell }}</span></div></details>
              </article>
            </li>
          </ol>
          <p v-if="sync?.warnings?.length" class="data-notice">В источнике есть дополнительные примечания. Проверяй условия занятий в исходной таблице.</p>
          <div class="schedule-bottom"><span>Особые даты и условия — в записи занятия</span><span>МСК · UTC+3</span></div>
        </section>
      </div>
      <footer><span><strong>misisync</strong><span class="footer-divider">/</span>Учёба в своём ритме</span><span>Неофициальный студенческий сервис</span></footer>
    </main>
  </div>
</template>
