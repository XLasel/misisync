"""Academic parity is a configurable estimate, never a source selection rule."""
from datetime import date, timedelta
from typing import Literal
from .domain import AcademicWeek, Window



def weeks(window: Window, settings) -> list[AcademicWeek]:
    anchor = settings.academic_reference_date
    anchor -= timedelta(days=anchor.weekday())
    monday = window.start - timedelta(days=window.start.weekday())
    result = []
    while monday <= window.end:
        alternate = ((monday - anchor).days // 7) % 2
        kind = settings.academic_reference_kind
        if alternate:
            kind = 'upper' if kind == 'lower' else 'lower'
        result.append(AcademicWeek(start=monday, end=monday + timedelta(days=6), kind=kind,
            reference_date=settings.academic_reference_date, reference_kind=settings.academic_reference_kind,
            explanation='Расчёт по чередованию от опорной недели, подтверждённой пользователем. '
                        'API МИСИС не сообщает тип недели. После каникул или изменения учебного графика '
                        'сверяйтесь с объявлениями института и расписанием университета.'))
        monday += timedelta(days=7)
    return result
