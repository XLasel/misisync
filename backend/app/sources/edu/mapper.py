import json
from collections import defaultdict
from datetime import timedelta
from ...domain import Evidence, Lesson, identity

# Verified in the supplied MISIS frontend; only applies to Moscow bell subset 3.
MOSCOW_BELLS = {
    ('3', str(30 - n), n): times for n, times in enumerate([
        ('09:00', '10:35'), ('10:50', '12:25'), ('12:40', '14:15'),
        ('14:30', '16:05'), ('16:20', '17:55'), ('18:00', '19:25'), ('19:35', '21:00'),
    ], 1)
}


def interval(start, end):
    if start is None and end is None:
        return None
    if not start or not end:
        raise ValueError('Incomplete upstream time interval')
    import re
    if any(not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?', v) for v in (start, end)):
        raise ValueError('Invalid upstream time')
    if start[:5] >= end[:5]:
        raise ValueError('Reversed upstream time interval')
    return start[:5], end[:5]


class EduMapper:
    def __init__(self, filial, url):
        self.filial, self.url = filial, url

    def normalize(self, result, group, monday, window):
        rows = [r for w in result.lists for r in w.rows]
        expected = {monday + timedelta(days=n) for n in range(6)}
        if len(rows) != 6 or {r.lesson_date for r in rows} != expected:
            raise ValueError('Incomplete calendar response: expected six dated rows')
        bells, appearances, cell_lessons = defaultdict(set), defaultdict(set), defaultdict(list)
        for row in rows:
            if row.lesson_date.weekday() != row.day_number - 1:
                raise ValueError('Date and weekday disagree')
            if len({c.key for c in row.cells}) != len(row.cells):
                raise ValueError('Duplicate bell cells')
            for cell in row.cells:
                time = interval(cell.bell_start, cell.bell_end)
                if time:
                    bells[cell.key].add(time)
                for lesson in cell.lessons:
                    appearances[row.lesson_date, lesson.lesson_index].add(cell.key)
                    cell_lessons[row.lesson_date, cell.key].append(lesson)
        normalized = []
        for row in rows:
            if not window.start <= row.lesson_date <= window.end:
                continue
            for cell in row.cells:
                for lesson in cell.lessons:
                    if lesson.subject_id is None and not lesson.subject_name:
                        continue  # Explicit empty placeholder, not an unknown subject.
                    if not lesson.subject_name:
                        raise ValueError('Missing lesson subject')
                    memberships = [g for g in lesson.ed_groups if g.group_id == group.id]
                    if not memberships:
                        raise ValueError('Lesson does not belong to requested group')
                    warnings = []
                    time = interval(lesson.lesson_start, lesson.lesson_end) or interval(cell.bell_start, cell.bell_end)
                    if time is None:
                        if len(bells[cell.key]) == 1:
                            time = next(iter(bells[cell.key]))
                        elif not bells[cell.key] and self.filial == 'MOSCOW' and cell.key in MOSCOW_BELLS:
                            time = MOSCOW_BELLS[cell.key]
                            warnings.append('Время по стандартной московской сетке звонков.')
                    if time is None:
                        warnings.append('Источник не позволяет однозначно определить время занятия.')
                    # Same lesson_index in adjacent pairs is normal (double period). Warn only when
                    # it also shares a cell with another lesson of the same subject — the case the
                    # university UI merges and our flat list can look wrong.
                    slots = appearances[row.lesson_date, lesson.lesson_index]
                    if len(slots) > 1 and any(
                        other.lesson_index != lesson.lesson_index and (
                            (lesson.subject_id and other.subject_id == lesson.subject_id) or
                            other.subject_name == lesson.subject_name)
                        for key in slots for other in cell_lessons[row.lesson_date, key]):
                        warnings.append('Источник повторяет эту запись в нескольких парах. Уточни время в официальном расписании.')
                    raw = lesson.model_dump(mode='json')
                    normalized.append(Lesson(
                        id=identity('edu_api', group.name, row.lesson_date.isoformat(), cell.key, raw),
                        group_id=group.name, date=row.lesson_date,
                        start_time=time[0] if time else None, end_time=time[1] if time else None,
                        subject=lesson.subject_name, lesson_type=lesson.lesson_type,
                        teachers=list(dict.fromkeys(t.teacher_name for t in lesson.teachers if t.teacher_name)),
                        rooms=list(dict.fromkeys(r.room_name for r in lesson.rooms if r.room_name)),
                        subgroup_ids=sorted({g.subgroup_number for g in memberships if g.subgroup_number is not None}),
                        warnings=warnings,
                        evidence=[Evidence(url=self.url,
                                           label=f'{row.lesson_date.isoformat()} · пара {cell.bell_number}',
                                           external_id=lesson.lesson_index, raw_text=json.dumps(raw, ensure_ascii=False))],
                    ))
        return normalized
