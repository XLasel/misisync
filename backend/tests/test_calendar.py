import asyncio
import copy
import io
from contextlib import asynccontextmanager
from datetime import date, timedelta

import httpx
import openpyxl
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain import Coverage, Evidence, Group, Lesson, Snapshot, SourceInfo, Window
from app.main import create_app
from app.ports import Document
from app.repositories.sqlite import Database
from app.sources.edu.source import EduApiSource
from app.sources.edu.schemas import CalendarResult, EduGroup
from app.sources.excel.source import ExcelSource
from app.sync import Synchronizer
from app.transports.http import HttpTransport

WINDOW = Window(start=date(2026, 9, 7), end=date(2026, 9, 20))
GROUP = 'МПИ-26-1-1'


def snapshot(source='excel', empty=False):
    return Snapshot(source=SourceInfo(id=source, label=source, url='https://example.test', basis='dated'),
                    coverage=Coverage(**WINDOW.model_dump()), groups=[Group(id=GROUP, name=GROUP)],
                    lessons=[] if empty else [Lesson(id='one', group_id=GROUP, date=WINDOW.start, subject='Math',
                                              evidence=[Evidence(url='https://example.test', label='cell', raw_text='Math')])])


@pytest.fixture
def database(tmp_path):
    db = Database(str(tmp_path / 'calendar.sqlite3'))
    db.initialize()
    return db


def test_atomic_replacement_idempotency_and_empty_calendar(database):
    original = snapshot()
    database.replace(original, 'first')
    database.replace(original, 'second')
    assert database.status().lesson_count == 1
    assert database.schedule(GROUP, WINDOW).lessons[0].id == 'one'
    # Deliberately duplicate a catalog PK: failure after DELETEs must roll back.
    with database.connect() as sql:
        sql.execute("CREATE TRIGGER reject_group BEFORE INSERT ON groups BEGIN SELECT RAISE(ABORT, 'test failure'); END")
    with pytest.raises(Exception, match='test failure'):
        database.replace(snapshot('edu_api'), 'failed')
    assert database.status().source.id == 'excel'
    assert database.status().last_success == 'second'
    assert database.status().lesson_count == 1
    with database.connect() as sql:
        sql.execute('DROP TRIGGER reject_group')
    database.replace(snapshot('edu_api', empty=True), 'third')
    assert database.status().source.id == 'edu_api'
    assert database.status().lesson_count == 0
    assert database.schedule(GROUP, WINDOW).available_dates == list(WINDOW.dates())
    reopened = Database(database.path)
    reopened.initialize()
    assert reopened.status().last_success == 'third'


def test_outside_coverage_unknown_group_and_invalid_snapshot(database):
    database.replace(snapshot(), 'good')
    outside = Window(start=date(2026, 10, 1), end=date(2026, 10, 3))
    assert database.schedule(GROUP, outside).available_dates == []
    assert database.schedule("' OR 1=1 --", WINDOW).group is None
    bad = snapshot()
    bad = bad.model_copy(update={'lessons': [bad.lessons[0].model_copy(update={'date': date(2027, 1, 1)})]})
    with pytest.raises(ValueError):
        database.replace(bad, 'bad')
    assert database.status().last_success == 'good'


class MemorySource:
    def __init__(self, data=None, fail=False):
        self.data, self.fail = data or snapshot(), fail
        self.info = self.data.source

    async def fetch(self, transport, window):
        if self.fail:
            raise ValueError('secret upstream payload')
        return self.data


@asynccontextmanager
async def no_network():
    yield None


def test_application_switch_failure_retains_actual_source(database):
    database.replace(snapshot('excel'), 'good')
    sync = Synchronizer(database, MemorySource(snapshot('edu_api'), fail=True), Settings(), no_network)
    assert asyncio.run(sync.run_once(window=WINDOW)) is False
    assert database.status().source.id == 'excel'
    assert 'secret' not in database.status().last_error
    sync.source = MemorySource(snapshot('edu_api'))
    assert asyncio.run(sync.run_once(window=WINDOW))
    assert database.status().source.id == 'edu_api'


def lesson(index='event', subject='Math', subgroup=None):
    return dict(lesson_index=index, subject_id='math', subject_name=subject, lesson_type='Лекционные',
                lesson_start=None, lesson_end=None, rooms=[{'room_name': 'Online'}],
                teachers=[{'teacher_name': 'Teacher'}],
                ed_groups=[dict(group_id='42', group_name=GROUP, subgroup_id='11' if subgroup else None, subgroup_number=subgroup)])


def calendar(monday=WINDOW.start, entries=None):
    rows = []
    for n in range(6):
        cells = [dict(bell_id=str(30-i), bell_subset_id='3', bell_number=i, bell_start=None, bell_end=None, lessons=[]) for i in range(1, 8)]
        if n == 0:
            cells[4]['lessons'] = entries if entries is not None else [lesson()]
        rows.append(dict(lesson_date=(monday + timedelta(days=n)).isoformat(), day_number=n+1, cells=cells))
    return {'lists': [{'week_number': monday.isocalendar()[1], 'rows': rows}]}


class RpcTransport:
    def __init__(self, failure=None, empty=False):
        self.failure, self.empty, self.calls = failure, empty, []

    async def request(self, method, url, *, body=None, headers=None):
        import json
        from urllib.parse import parse_qs
        request = json.loads(body)
        self.calls.append(request)
        if request['method'].endswith('getFillialInfo'):
            result = {'groups': [dict(id='42', name=GROUP, subgroups=[dict(id='11', number=1)])]}
        else:
            params = parse_qs(request['params'][0])
            monday = date.fromisoformat(params['begin_date'][0])
            if self.failure == 'rpc':
                return Document(url, b'{"jsonrpc":"2.0","id":1,"error":{"message":"fail"}}')
            result = calendar(monday, [] if self.empty else None)
            if self.failure == 'partial' and monday > WINDOW.start:
                result['lists'][0]['rows'].pop()
        return Document(url, json.dumps(dict(jsonrpc='2.0', id=1, result=result)).encode())


def test_edu_dates_explicit_subgroups_empty_days_and_unknown_group():
    source = EduApiSource(Settings(edu_groups=(GROUP,), edu_request_delay_seconds=0))
    transport = RpcTransport()
    data = asyncio.run(source.fetch(transport, WINDOW))
    assert [l.date for l in data.lessons] == [WINDOW.start, WINDOW.start + timedelta(days=7)]
    assert len({l.id for l in data.lessons}) == 2  # Same upstream ID, separate calendar dates.
    assert data.lessons[0].start_time == '16:20'
    assert data.coverage.includes(date(2026, 9, 8))
    assert not data.coverage.includes(date(2026, 9, 13))
    assert data.groups[0].subgroups == [1]
    assert len(transport.calls) == 3
    empty = asyncio.run(source.fetch(RpcTransport(empty=True), WINDOW))
    assert empty.lessons == []
    with pytest.raises(ValueError, match='missing'):
        asyncio.run(EduApiSource(Settings(edu_groups=('unknown',), edu_request_delay_seconds=0)).fetch(RpcTransport(), WINDOW))


@pytest.mark.parametrize('failure', ['rpc', 'partial'])
def test_edu_partial_or_rpc_error_keeps_entire_snapshot(database, failure):
    database.replace(snapshot(), 'good')
    config = Settings(edu_groups=(GROUP,), edu_request_delay_seconds=0)
    sync = Synchronizer(database, EduApiSource(config), config, no_network)
    assert not asyncio.run(sync.run_once(RpcTransport(failure), WINDOW))
    assert database.status().last_success == 'good'
    assert database.status().source.id == 'excel'


def test_edu_mapper_preserves_types_and_flags_repeated_slots():
    source = EduApiSource(Settings(edu_request_delay_seconds=0))
    raw = calendar(entries=[lesson(), {**lesson('lab', subgroup=1), 'lesson_type': 'Лабораторные'}])
    raw['lists'][0]['rows'][0]['cells'][5]['lessons'] = [lesson()]
    group = EduGroup(id='42', name=GROUP, subgroups=[])
    records = source.mapper.normalize(CalendarResult.model_validate(raw), group, WINDOW.start, WINDOW)
    assert len(records) == 3
    assert records[1].subgroup_ids == [1]
    assert records[0].warnings and records[2].warnings
    assert records[0].start_time != records[2].start_time
    assert len({l.id for l in records}) == 3


def test_conflicting_bells_are_not_guessed():
    source = EduApiSource(Settings(edu_filial='OTHER'))
    raw = calendar()
    for n, start in [(1, '16:00:00'), (2, '16:20:00')]:
        cell = raw['lists'][0]['rows'][n]['cells'][4]
        cell['bell_start'], cell['bell_end'] = start, '17:55:00'
    records = source.mapper.normalize(CalendarResult.model_validate(raw), EduGroup(id='42', name=GROUP, subgroups=[]), WINDOW.start, WINDOW)
    assert records[0].start_time is None
    assert records[0].warnings


class ExcelTransport:
    def __init__(self, corrupt=False):
        self.corrupt = corrupt
    async def request(self, method, url, **kwargs):
        if url.endswith('/students/'):
            return Document(url, b'<a href="/schedule/one.xlsx">Institute</a>')
        if self.corrupt:
            return Document(url, b'invalid')
        book = openpyxl.Workbook()
        sheet = book.active
        sheet.append(['Группа', 'День', 'Начало', 'Конец', 'Предмет', 'Неделя'])
        sheet.append([GROUP, 'Понедельник', '09:00', '10:35', 'Odd math', 'нечётная'])
        sheet.append([GROUP, 'Понедельник', '09:00', '10:35', 'Even math', 'чётная'])
        stream = io.BytesIO()
        book.save(stream)
        return Document(url, stream.getvalue())


def test_excel_projection_uses_academic_anchor_not_iso_parity():
    source = ExcelSource(Settings(excel_term_start=date(2026, 9, 1)))
    data = asyncio.run(source.fetch(ExcelTransport(), WINDOW))
    assert [(l.date, l.subject) for l in data.lessons] == [(date(2026, 9, 7), 'Even math'), (date(2026, 9, 14), 'Odd math')]
    assert data.source.basis == 'weekly_template'
    with pytest.raises(ValueError):
        asyncio.run(source.fetch(ExcelTransport(corrupt=True), WINDOW))


@pytest.mark.parametrize('provider', ['excel', 'edu_api'])
def test_same_public_contract_for_both_sources(tmp_path, provider):
    settings = Settings(database_path=str(tmp_path / 'api.sqlite3'), enable_scheduler=False, edu_groups=(GROUP,), edu_request_delay_seconds=0)
    source = ExcelSource(settings) if provider == 'excel' else EduApiSource(settings)
    transport = ExcelTransport() if provider == 'excel' else RpcTransport()
    app = create_app(settings, source=source)
    with TestClient(app) as client:
        assert asyncio.run(app.state.synchronizer.run_once(transport, WINDOW))
        groups = client.get('/api/groups').json()
        assert groups['groups'][0]['id'] == GROUP
        response = client.get('/api/schedule', params={'group_id': GROUP, 'start': '2026-09-07', 'end': '2026-09-20'})
        assert response.status_code == 200
        data = response.json()
        assert data['lessons'] and data['revision'] == groups['revision']
        assert all(set(l) == {'id','group_id','date','start_time','end_time','subject','lesson_type','teachers','rooms','subgroup_ids','subgroup_label','notes','warnings','evidence'} for l in data['lessons'])
        assert client.get('/api/catalog').status_code == 404
        assert client.get('/api/schedule', params={'group_id': GROUP, 'start': '2026-09-20', 'end': '2026-09-07'}).status_code == 422


@pytest.mark.parametrize('failure', ['http', 'oversize', 'timeout'])
def test_http_transport_failures(failure):
    def handler(request):
        if failure == 'timeout':
            raise httpx.ReadTimeout('Timeout', request=request)
        return httpx.Response(503 if failure == 'http' else 200, content=b'x'*2048)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with HttpTransport(Settings(max_download_bytes=1024), client=client) as transport:
                with pytest.raises((httpx.HTTPError, ValueError)):
                    await transport.request('GET', 'https://example.test')
    asyncio.run(run())


def test_excel_discovery_deduplicates_and_bad_second_file_preserves_snapshot(database):
    class TwoFiles(ExcelTransport):
        async def request(self, method, url, **kwargs):
            if url.endswith('/students/'):
                return Document(url, b'<a href="/one.xlsx">One</a><a href="/one.xlsx">Again</a><a href="/two.xlsx">Two</a><a href="https://other.test/out.xlsx">Other</a>')
            if url.endswith('two.xlsx'):
                return Document(url, b'invalid workbook')
            assert url.endswith('one.xlsx')
            return await super().request(method, url, **kwargs)
    database.replace(snapshot(), 'good')
    sync = Synchronizer(database, ExcelSource(Settings()), Settings(), no_network)
    assert not asyncio.run(sync.run_once(TwoFiles(), WINDOW))
    assert database.status().last_success == 'good'
    assert database.status().lesson_count == 1


def test_updates_serialize_and_readers_keep_previous_snapshot(database):
    database.replace(snapshot(), 'good')
    async def run():
        entered, proceed = asyncio.Event(), asyncio.Event()
        class SlowSource(MemorySource):
            calls = 0
            async def fetch(self, transport, window):
                self.calls += 1
                entered.set()
                await proceed.wait()
                return self.data
        source = SlowSource(snapshot('edu_api'))
        sync = Synchronizer(database, source, Settings(), no_network)
        first = asyncio.create_task(sync.run_once(window=WINDOW))
        await entered.wait()
        second = asyncio.create_task(sync.run_once(window=WINDOW))
        await asyncio.sleep(0)
        assert source.calls == 1
        assert sync.updating
        assert database.status().source.id == 'excel'
        proceed.set()
        assert all(await asyncio.gather(first, second))
        assert source.calls == 2
        assert not sync.updating
    asyncio.run(run())
    assert database.status().source.id == 'edu_api'


def test_api_source_does_not_import_excel_parser():
    import os
    import subprocess
    import sys
    from pathlib import Path
    environment = {**os.environ, 'SCHEDULE_SOURCE': 'edu_api', 'PYTHONPATH': str(Path(__file__).resolve().parents[1])}
    result = subprocess.run([sys.executable, '-c',
        "import sys; from app.main import app; assert 'app.sources.excel.parser' not in sys.modules; assert 'openpyxl' not in sys.modules"],
        env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_duplicate_calendar_entry_keeps_all_provenance():
    from app.domain import merge_duplicates
    first = snapshot().lessons[0]
    second = first.model_copy(update={'evidence': [Evidence(url='https://other.test', label='other cell', raw_text='Math')]})
    merged = merge_duplicates([first, first, second])
    assert len(merged) == 1
    assert len(merged[0].evidence) == 2
    with pytest.raises(ValueError, match='Conflicting'):
        merge_duplicates([first, first.model_copy(update={'subject': 'Different'})])
