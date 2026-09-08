import asyncio
import io
import sqlite3
from dataclasses import replace

import httpx
import openpyxl
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import Database
from app.main import create_app
from app.parser import Lesson, ParseError, Sheet, consolidate, grid_table, parse_workbook
from app.sync import Synchronizer, discover, download


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
def database(tmp_path):
    db = Database(str(tmp_path / 'db.sqlite3'))
    db.initialize()
    return db


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


def test_idempotency_updates_and_removals(database, lesson):
    database.replace([lesson, lesson], {lesson.group_name}, 'first', 'url', [])
    first_id = database.schedule(lesson.group_name)[0]['id']
    database.replace([lesson], {lesson.group_name}, 'second', 'url', [])
    assert len(database.schedule(lesson.group_name)) == 1
    assert database.schedule(lesson.group_name)[0]['id'] == first_id
    database.replace([replace(lesson, room='Б-202')], {lesson.group_name}, 'third', 'url', [])
    assert [l['room'] for l in database.schedule(lesson.group_name)] == ['Б-202']
    assert database.status()['last_success'] == 'third'


def test_transaction_rolls_back_on_constraint_error(database, lesson):
    database.replace([lesson], {lesson.group_name}, 'good', 'url', [])
    with pytest.raises(sqlite3.IntegrityError):
        database.replace([replace(lesson, weekday=9)], {lesson.group_name}, 'bad', 'url', [])
    assert database.schedule(lesson.group_name)[0]['weekday'] == 0
    assert database.status()['last_success'] == 'good'


def test_empty_import_preserves_database(database, lesson):
    database.replace([lesson], {lesson.group_name}, 'good', 'url', [])
    with pytest.raises(ValueError):
        database.replace([], set(), 'bad', 'url', [])
    reopened = Database(database.path)
    reopened.initialize()
    assert reopened.status()['lesson_count'] == 1
    assert reopened.status()['last_success'] == 'good'


def test_discovery_follows_schedule_and_deduplicates():
    responses = {
        '/students/': '<a href="/students/schedule/">Расписание учебных занятий (xls)</a>',
        '/students/schedule/': '<a href="/files/ikn.xls">ИКН</a><a href="/files/ibo.xlsx">ИБО</a><a href="/files/ikn.xls">Дубль</a><a href="https://foreign.test/x.xlsx">external</a>',
    }

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=responses[r.url.path]))) as client:
            urls = await discover(client, Settings())
            assert urls == ['https://misis.ru/files/ibo.xlsx', 'https://misis.ru/files/ikn.xls']
            filtered = await discover(client, Settings(source_link_pattern='ИКН'))
            assert filtered == ['https://misis.ru/files/ikn.xls']
    asyncio.run(run())


@pytest.mark.parametrize('failure', ['http', 'corrupt', 'empty', 'timeout'])
def test_failed_refresh_keeps_previous_snapshot(database, lesson, failure):
    database.replace([lesson], {lesson.group_name}, 'last-good', 'url', [])

    def handler(request):
        if failure == 'timeout':
            raise httpx.ReadTimeout('timeout', request=request)
        return httpx.Response(503 if failure == 'http' else 200, content=b'corrupt' if failure == 'corrupt' else b'')

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            assert not await Synchronizer(database, Settings(source_url='https://misis.ru/file.xlsx')).run_once(client)
    asyncio.run(run())
    assert database.status()['last_success'] == 'last-good'
    assert database.status()['last_error']
    assert database.status()['lesson_count'] == 1


def test_one_bad_institute_rolls_back_entire_refresh(database, lesson, flat_bytes):
    database.replace([lesson], {lesson.group_name}, 'old', 'url', [])

    def handler(request):
        if request.url.path == '/students/':
            return httpx.Response(200, text='<a href="/a.xlsx">A</a><a href="/b.xlsx">B</a>')
        return httpx.Response(200, content=flat_bytes if request.url.path == '/a.xlsx' else b'invalid')

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            assert not await Synchronizer(database, Settings()).run_once(client)
    asyncio.run(run())
    assert database.status()['last_success'] == 'old'
    assert database.status()['lesson_count'] == 1


def test_successful_refresh_twice(database, flat_bytes):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=flat_bytes))) as client:
            sync = Synchronizer(database, Settings(source_url='https://misis.ru/test.xlsx'))
            assert await sync.run_once(client)
            assert await sync.run_once(client)
    asyncio.run(run())
    assert database.status()['lesson_count'] == 2
    assert database.status()['last_success']
    assert database.status()['last_error'] is None


def test_download_size_limit():
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b'x' * 2000))) as client:
            with pytest.raises(ValueError, match='MAX_DOWNLOAD_BYTES'):
                await download(client, 'https://misis.ru/test.xlsx', 1000)
    asyncio.run(run())


def test_api_filtering_validation_and_persistence(tmp_path, lesson):
    app = create_app(Settings(database_path=str(tmp_path / 'api.sqlite3'), enable_scheduler=False))
    with TestClient(app) as client:
        assert client.get('/api/health').status_code == 200
        assert client.get('/api/status').json()['last_success'] is None
        app.state.db.replace([lesson, replace(lesson, weekday=1)], {lesson.group_name}, 'now', 'url', [])
        assert client.get('/api/groups').json() == [lesson.group_name]
        response = client.get('/api/schedule', params={'group': lesson.group_name, 'weekday': 1})
        assert len(response.json()) == 1 and response.json()[0]['weekday'] == 1
        assert client.get('/api/schedule', params={'group': "' OR 1=1 --"}).json() == []
        assert client.get('/api/schedule?weekday=7').status_code == 422
        assert client.get('/api/status').json()['lesson_count'] == 2
    with TestClient(app) as client:
        assert client.get('/api/status').json()['lesson_count'] == 2
