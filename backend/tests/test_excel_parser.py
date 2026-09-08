import io
from dataclasses import replace
import openpyxl
import pytest
from app.sources.excel.parser import Lesson, ParseError, Sheet, consolidate, grid_table, parse_workbook

def workbook(rows):
    book = openpyxl.Workbook()
    sheet = book.active
    for row in rows:
        sheet.append(row)
    output = io.BytesIO()
    book.save(output)
    return output.getvalue()


@pytest.fixture
def lesson():
    return Lesson('БИВТ-26-1', 0, '09:00', '10:35', 'Математика', 'Лекционные', 'Иванов И. И.', 'Б-101', raw_text='Математика (Лекционные)\nИванов И. И.')


@pytest.fixture
def flat_bytes():
    return workbook([
        ['Группа', 'День', 'Начало', 'Конец', 'Предмет', 'Преподаватель', 'Аудитория', 'Подгруппа', 'Неделя'],
        ['БИВТ-26-1', 'Понедельник', '09:00', '10:35', 'Математика', 'Иванов И. И.', 'Б-101', '1', 'нечётная'],
        ['БИВТ-26-1', 'Вторник', '10:50', '12:25', 'Физика', '', '', '', 'все'],
    ])


def test_xlsx_fields_and_missing_values(flat_bytes):
    lessons, groups, _ = parse_workbook(flat_bytes)
    assert groups == {'БИВТ-26-1'}
    assert lessons[0].teacher == 'Иванов И. И.'
    assert lessons[0].week_pattern == 'odd'
    assert lessons[0].subgroup == '1'
    assert lessons[1].teacher == lessons[1].room == ''
    assert lessons[1].weekday == 1


def test_merged_days_weeks_and_subgroups():
    # The production grid has two week rows, two subgroup lanes, separate rooms.
    cells = [['Дата', 'Номер', 'Время', 'БИВТ-26-1', '', '', ''],
             ['', '', '', 1, '', 2, ''],
             ['Понедельник', '1', '09:00:00 - 10:35:00', 'Алгебра (Лекционные)\nИванов И. И.', 'Б-101', 'Физика (Лабораторные)', 'Б-102'],
             ['', '', '', 'Геометрия (Практические)', 'Б-103', '', '']]
    spans = {}
    for span in [(0, 1, 3, 7), (2, 4, 0, 1), (2, 4, 2, 3)]:
        for r in range(span[0], span[1]):
            for c in range(span[2], span[3]):
                spans[r, c] = span
    records, _ = grid_table(Sheet('1 курс', cells, spans), 'https://misis.ru/test.xls', 'odd')
    assert [(l.subject, l.week_pattern) for l in records] == [('Алгебра', 'odd'), ('Геометрия', 'even'), ('Физика', 'odd')]
    assert records[0].subgroup == '1 подгруппа'
    assert records[2].subgroup == '2 подгруппа'
    assert records[0].teacher == 'Иванов И. И.'
    assert records[1].weekday == 0
    assert records[1].end_time == '10:35'


def test_ibo_vertical_day_teacher_continuation_and_merged_room():
    cells = [['ГРУППЫ', '', 'БЛГ-26-1', ''],
             ['А', '09.00-09.45', 'История', ''],
             ['Д', '09.50-10.35', 'Иванов И.И.', 'Б101'],
             ['Е', '10.50-11.35', 'Грамматика', ''],
             ['Р', '11.40-12.25', '', ''],
             ['С', '12.40-13.25', '', '']]
    spans = {(2, 0): (2, 3, 0, 1), (3, 2): (3, 4, 2, 4), (3, 3): (3, 4, 2, 4)}
    records, _ = grid_table(Sheet('ИБО', cells, spans), 'source', 'odd')
    assert records[0].weekday == 2
    assert records[0].end_time == '10:35'
    assert records[0].teacher == 'Иванов И.И.'
    assert records[0].room == 'Б101'
    assert records[1].room == ''


def test_consolidates_equal_weeks_but_preserves_different_rooms(lesson):
    same = consolidate([replace(lesson, week_pattern='odd'), replace(lesson, week_pattern='even')])
    assert len(same) == 1 and same[0].week_pattern == 'all'
    different = consolidate([replace(lesson, week_pattern='odd'), replace(lesson, week_pattern='even', room='Г-500')])
    assert len(different) == 2


@pytest.mark.parametrize('data', [b'<html>Service unavailable</html>', b'', workbook([['Not a schedule']])])
def test_invalid_sources_are_rejected(data):
    with pytest.raises(ParseError):
        parse_workbook(data)
