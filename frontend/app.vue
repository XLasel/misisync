<script setup lang="ts">
import { normalizeGroupSearch, scheduleCards, addDays, moscowToday } from '~/utils/schedule'
import type { Lesson } from '~/types/schedule'
const { catalog, catalogError, group, weekStart, weekEnd, weekDates, schedule, scheduleError, loading, reload } = useSchedule()
const days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
const shortDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
const query = ref('')
const institute = ref('')
const level = ref('')
const weekday = ref(0)
const subgroup = ref('all')
const pickerOpen = ref(false)
const activeOption = ref(0)
const searchInput = ref<HTMLInputElement>()
const institutes = computed(() => [...new Set(catalog.value.flatMap(g => g.institutes))].sort((a, b) => a.localeCompare(b, 'ru')))
const levels = computed(() => [...new Set(catalog.value.map(g => g.education_level).filter(Boolean))])
const matches = computed(() => catalog.value.filter(g =>
  normalizeGroupSearch(g.name).includes(normalizeGroupSearch(query.value)) &&
  (!institute.value || g.institutes.includes(institute.value)) && (!level.value || g.education_level === level.value)))
const options = computed(() => matches.value.slice(0, 60))
const selectedGroup = computed(() => catalog.value.find(g => g.id === group.value))
const subgroups = computed(() => [...new Set([...(selectedGroup.value?.subgroups || []), ...(schedule.value?.lessons || []).flatMap(l => l.subgroup_ids)])].sort((a, b) => a - b))
const cards = computed(() => scheduleCards(schedule.value?.lessons || [], subgroup.value))
const lessons = computed(() => cards.value.filter(l => l.date === weekDates.value[weekday.value]))
const kind = (lesson: Lesson) => /лек/i.test(lesson.lesson_type) ? 'lecture' : /лаб/i.test(lesson.lesson_type) ? 'lab' : /прак|семин|^пр\.?$/i.test(lesson.lesson_type) ? 'practice' : 'other'
const kindLabel = (lesson: Lesson) => ({ lecture: 'Лекция', practice: 'Практика', lab: 'Лабораторная', other: lesson.lesson_type || 'Занятие' })[kind(lesson)]
const subgroupLabel = (lesson: Lesson) => {
  if (lesson.subgroup_ids.length) return `Подгрупп${lesson.subgroup_ids.length === 1 ? 'а' : 'ы'} ${lesson.subgroup_ids.join(', ')}`
  const label = lesson.subgroup_label?.trim()
  return label || ''
}
const dateLabel = (value: string) => new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short', timeZone: 'UTC' }).format(new Date(`${value}T12:00:00Z`))
const calendarLabel = computed(() => `${dateLabel(weekStart.value)} — ${dateLabel(weekEnd.value)}`)
const dayAvailable = computed(() => schedule.value?.available_dates.includes(weekDates.value[weekday.value]!) || false)
const sourceUrl = computed(() => schedule.value?.source?.url || 'https://edu.misis.ru/schedule?filial=MOSCOW')
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
  if (import.meta.client) {
    localStorage.setItem('misisync-group', value)
    subgroup.value = localStorage.getItem(`misisync-subgroup:${value}`) || 'all'
  }
})
watch([subgroups, loading], ([values, state]) => {
  if (state === 'success' && subgroup.value !== 'all' && !values.includes(Number(subgroup.value))) subgroup.value = 'all'
})
watch(subgroup, value => {
  if (import.meta.client && group.value) localStorage.setItem(`misisync-subgroup:${group.value}`, value)
})
onMounted(() => {
  const saved = localStorage.getItem('misisync-group') || ''
  if (catalog.value.some(g => g.id === saved)) selectGroup(saved)
  weekday.value = (new Date(`${moscowToday()}T12:00:00Z`).getUTCDay() + 6) % 7
})
watch(catalog, values => {
  if (group.value && !values.some(g => g.id === group.value)) group.value = ''
  if (!group.value && import.meta.client) {
    const saved = localStorage.getItem('misisync-group') || ''
    if (values.some(g => g.id === saved)) selectGroup(saved)
  }
})
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <a class="brand" href="/" aria-label="Misisync, главная"><img src="/favicon.svg" alt="" width="37" height="37"><span>misi<span class="brand-light">sync</span><sup>β</sup></span></a>
      <span class="header-context">Расписание МИСИС</span>
      <a class="source-link" :href="sourceUrl" target="_blank" rel="noopener noreferrer">Источник <span aria-hidden="true">↗</span></a>
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
                  <li v-for="(item, i) in options" :id="`group-option-${i}`" :key="item.name" role="option" :aria-selected="item.id === group" :class="{ highlighted: i === activeOption }" @mousedown.prevent @click="selectGroup(item.id)"><strong>{{ item.name }}</strong><span>{{ item.education_level || 'Уровень не указан' }}</span></li>
                </ul>
                <p v-if="!matches.length" class="search-help">Попробуй часть названия или сбрось уточнения.</p>
                <p v-if="matches.length > options.length" class="search-help">Показаны первые 60. Введи название группы.</p>
              </div>
            </div>
            <details class="search-refinements"><summary>Уточнить поиск <span v-if="institute || level" class="filter-count">{{ Number(!!institute) + Number(!!level) }}</span></summary>
              <div class="refinements-content">
                <template v-if="institutes.length"><label for="institute">Институт</label><select id="institute" v-model="institute"><option value="">Все институты</option><option v-for="name in institutes" :key="name" :value="name">{{ name }}</option></select></template>
                <label for="level">Уровень образования</label><select id="level" v-model="level"><option value="">Все уровни</option><option v-for="name in levels" :key="name" :value="name">{{ name }}</option></select>
                <button v-if="institute || level" class="text-button" @click="resetSearch">Сбросить уточнения</button>
              </div>
            </details>
            <div v-if="selectedGroup" class="selected-group"><span class="overline">ВЫБРАННАЯ ГРУППА</span><strong>{{ selectedGroup.name }}</strong><span>{{ selectedGroup.education_level }}</span><p v-for="name in selectedGroup.institutes" :key="name">{{ name }}</p></div>
            <p v-else class="hint">Начни вводить название. Институт и уровень можно не выбирать.</p>
          </section>
          <p class="sidebar-note">Группа и подгруппа сохраняются<br>на этом устройстве.</p>
        </aside>
        <section class="schedule-panel" aria-label="Расписание занятий">
          <div class="schedule-heading"><div><span class="overline">РАСПИСАНИЕ ЗАНЯТИЙ</span><h2>{{ group || 'Твоя учебная неделя' }}</h2></div></div>
          <div v-if="group" class="schedule-controls">
            <div class="week-control calendar-control"><button aria-label="Предыдущая неделя" @click="weekStart = addDays(weekStart, -7)">‹</button><span aria-live="polite">{{ calendarLabel }}</span><button aria-label="Следующая неделя" @click="weekStart = addDays(weekStart, 7)">›</button></div>
            <div v-if="subgroups.length" class="subgroup-control" aria-label="Фильтр по подгруппе"><span>Подгруппа</span><div class="segmented"><button :aria-pressed="subgroup === 'all'" :class="{ active: subgroup === 'all' }" @click="subgroup = 'all'">Все</button><button v-for="id in subgroups" :key="id" :aria-label="`Подгруппа ${id}`" :aria-pressed="subgroup === String(id)" :class="{ active: subgroup === String(id) }" @click="subgroup = String(id)">{{ id }}</button></div></div>
            <span v-else-if="loading === 'success'" class="no-subgroups">Подгруппы в источнике не указаны</span>
          </div>
          <nav class="day-tabs" aria-label="Дни недели"><button v-for="(day, i) in days" :key="day" :aria-label="day" :aria-pressed="weekday === i" :class="{ active: weekday === i }" @click="weekday = i"><span>{{ shortDays[i] }}</span><span class="day-count">{{ group && schedule?.available_dates.includes(weekDates[i]!) ? cards.filter(l => l.date === weekDates[i]).length : '—' }}</span></button></nav>
          <div class="day-heading"><h3>{{ days[weekday] }} <small>{{ dateLabel(weekDates[weekday]!) }}</small></h3><span>{{ group && dayAvailable && loading !== 'pending' ? `Занятий: ${lessons.length}` : 'Время московское' }}</span></div>
          <p v-if="subgroup !== 'all' && group" class="filter-note">Подгруппа {{ subgroup }} + общие занятия. Записи без уточнения подгруппы тоже показаны.</p>
          <div v-if="catalogError || (group && scheduleError)" class="empty-state" role="alert"><span class="empty-symbol">↻</span><h3>Не удалось получить расписание</h3><p>Проверь подключение и попробуй ещё раз.</p><button class="primary-button" @click="reload">Повторить</button></div>
          <div v-else-if="!group" class="empty-state"><span class="empty-symbol" aria-hidden="true">▦</span><h3>Какая у тебя группа?</h3><p>{{ catalog.length ? 'Найди её по названию. Мы покажем пары и запомним твой выбор.' : 'Список групп ещё загружается.' }}</p><button v-if="catalog.length" class="primary-button" @click="searchInput?.focus()">Найти группу <span aria-hidden="true">↗</span></button></div>
          <div v-else-if="loading === 'pending' && !schedule" class="empty-state" role="status"><span class="empty-symbol">⋯</span><h3>Загружаем занятия</h3></div>
          <div v-else-if="!dayAvailable" class="empty-state"><span class="empty-symbol">◷</span><h3>Данные за этот день не загружены</h3><p>Выбери день с понедельника по субботу. Воскресенье в источнике не отдаётся.</p></div>
          <div v-else-if="!lessons.length" class="empty-state"><span class="empty-symbol" aria-hidden="true">☀</span><h3>В расписании нет занятий</h3><p>Для этого дня, недели и подгруппы пары не указаны в источнике.</p></div>
          <ol v-else class="lessons" :class="{ refreshing: loading === 'pending' && !!schedule }">
            <li v-for="lesson in lessons" :key="lesson.id" class="lesson-row"><div class="time-column"><strong>{{ lesson.start_time || '—' }}</strong><span>{{ lesson.end_time || 'Время не указано' }}</span></div>
              <article class="lesson-card" :class="kind(lesson)">
                <div class="lesson-top"><span class="type-label"><i></i>{{ kindLabel(lesson) }}</span><span v-if="subgroupLabel(lesson)" class="subgroup-tag">{{ subgroupLabel(lesson) }}</span></div>
                <h4>{{ lesson.subject }}</h4>
                <div v-if="lesson.teachers.length || lesson.rooms.length" class="lesson-meta"><span v-if="lesson.teachers.length">{{ lesson.teachers.join(', ') }}</span><span v-if="lesson.rooms.length" class="room"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2"/></svg>{{ lesson.rooms.join(', ') }}</span></div>
                <p v-for="note in [...lesson.notes, ...lesson.warnings]" :key="note" class="lesson-notes">{{ note }}</p>
                <details class="source-details"><summary>Запись в источнике</summary><div v-for="(original, i) in lesson.evidence" :key="i" class="source-record"><p>{{ original.raw_text }}</p><span>{{ original.label }}</span></div></details>
              </article>
            </li>
          </ol>
          <div class="schedule-bottom"><span>Особые даты и условия — в записи занятия</span><span>МСК · UTC+3</span></div>
        </section>
      </div>
      <footer><span><strong>misisync</strong><span class="footer-divider">/</span>Учёба в своём ритме</span><span>Неофициальный студенческий сервис</span></footer>
    </main>
  </div>
</template>
