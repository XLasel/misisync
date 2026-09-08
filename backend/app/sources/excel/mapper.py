from datetime import timedelta
from ...domain import Coverage, Evidence, Group, Lesson, Snapshot, identity, merge_duplicates
from ..classification import education_level, institute_name, subgroup_ids
from .parser import ParseError, parse_workbook


class ExcelMapper:
    def __init__(self, settings, info):
        self.settings, self.info = settings, info

    def map(self, documents, window):
        templates, catalog, warnings = [], {}, []
        for document, label in documents:
            final_url = document.url
            parsed, names, notes = parse_workbook(document.content, final_url, self.settings.excel_upper_row_week)
            templates.extend(parsed)
            institute = institute_name(final_url, label)
            for name in names:
                catalog.setdefault(name, set())
                if institute:
                    catalog[name].add(institute)
            warnings.extend(notes)
        if not templates:
            raise ParseError('No lessons found in selected Excel sources')
        groups = [Group(id=name, name=name, institutes=sorted(institutes), education_level=education_level(name),
                        subgroups=sorted({i for row in templates if row.group_name == name for i in subgroup_ids(row.subgroup)}))
                  for name, institutes in sorted(catalog.items())]
        lessons = []
        anchor = self.settings.excel_term_start
        anchor -= timedelta(days=anchor.weekday())
        for day in window.dates():
            if day < self.settings.excel_term_start or day > self.settings.excel_term_end:
                continue
            pattern = 'odd' if ((day - anchor).days // 7) % 2 == 0 else 'even'
            for row in templates:
                if row.weekday != day.weekday() or row.week_pattern not in ('all', pattern):
                    continue
                lessons.append(Lesson(
                    id=identity(self.info.id, day.isoformat(), row.record()['id']), group_id=row.group_name,
                    date=day, start_time=row.start_time or None, end_time=row.end_time or None,
                    subject=row.subject, lesson_type=row.lesson_type,
                    teachers=[row.teacher] if row.teacher else [], rooms=[row.room] if row.room else [],
                    subgroup_ids=subgroup_ids(row.subgroup), subgroup_label=row.subgroup,
                    notes=[row.notes] if row.notes else [],
                    evidence=[Evidence(url=row.source_url, label=f'{row.source_sheet} · {row.source_cell}', raw_text=row.raw_text)],
                ))
        start, end = max(window.start, self.settings.excel_term_start), min(window.end, self.settings.excel_term_end)
        if start > end:
            raise ValueError('Sync window does not intersect the configured Excel term')
        return Snapshot(source=self.info, coverage=Coverage(start=start, end=end), groups=groups, lessons=merge_duplicates(lessons),
                        warnings=sorted(set(warnings + ['Расписание развёрнуто из недельного шаблона. Особые даты и условия проверяй в исходной записи.'])))
