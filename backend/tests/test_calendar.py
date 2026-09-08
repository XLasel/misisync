import asyncio
import json
from contextlib import asynccontextmanager
from datetime import date, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain import Evidence, Group, Lesson, Snapshot, SourceInfo, Window, merge_duplicates
from app.main import create_app
from app.ports import Document
from app.sources.edu.schemas import CalendarResult, EduGroup
from app.sources.edu.source import EduApiSource
from app.transports.http import HttpTransport

WINDOW = Window(start=date(2026, 9, 7), end=date(2026, 9, 20))
GROUP = 'МПИ-26-1-1'


def lesson(index='event', subject='Math', subgroup=None):
    return dict(lesson_index=index, subject_id='math', subject_name=subject, lesson_type='Лекционные',
                lesson_start=None, lesson_end=None, rooms=[{'room_name': 'Online'}],
                teachers=[{'teacher_name': 'Teacher'}],
                ed_groups=[dict(group_id='42', group_name=GROUP, subgroup_id='11' if subgroup else None, subgroup_number=subgroup)])


def calendar(monday=WINDOW.start, entries=None):
    rows = []
    for n in range(6):
        cells = [dict(bell_id=str(30 - i), bell_subset_id='3', bell_number=i, bell_start=None, bell_end=None, lessons=[]) for i in range(1, 8)]
        if n == 0:
            cells[4]['lessons'] = entries if entries is not None else [lesson()]
        rows.append(dict(lesson_date=(monday + timedelta(days=n)).isoformat(), day_number=n + 1, cells=cells))
    return {'lists': [{'week_number': monday.isocalendar()[1], 'rows': rows}]}


class RpcTransport:
    def __init__(self, failure=None, empty=False):
        self.failure, self.empty, self.calls = failure, empty, []

    async def request(self, method, url, *, body=None, headers=None):
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
    assert len({l.id for l in data.lessons}) == 2
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
def test_edu_batch_fetch_rejects_partial_or_rpc_error(failure):
    source = EduApiSource(Settings(edu_groups=(GROUP,), edu_request_delay_seconds=0))
    with pytest.raises(ValueError):
        asyncio.run(source.fetch(RpcTransport(failure), WINDOW))


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


def test_edu_mapper_allows_double_period_same_id_without_warning():
    source = EduApiSource(Settings(edu_request_delay_seconds=0))
    raw = calendar(entries=[lesson()])
    raw['lists'][0]['rows'][0]['cells'][5]['lessons'] = [lesson()]
    records = source.mapper.normalize(CalendarResult.model_validate(raw), EduGroup(id='42', name=GROUP, subgroups=[]), WINDOW.start, WINDOW)
    assert len(records) == 2
    assert records[0].start_time != records[1].start_time
    assert all('повторяет' not in w for item in records for w in item.warnings)


def test_conflicting_bells_are_not_guessed():
    source = EduApiSource(Settings(edu_filial='OTHER'))
    raw = calendar()
    for n, start in [(1, '16:00:00'), (2, '16:20:00')]:
        cell = raw['lists'][0]['rows'][n]['cells'][4]
        cell['bell_start'], cell['bell_end'] = start, '17:55:00'
    records = source.mapper.normalize(CalendarResult.model_validate(raw), EduGroup(id='42', name=GROUP, subgroups=[]), WINDOW.start, WINDOW)
    assert records[0].start_time is None
    assert records[0].warnings


def test_live_public_contract():
    settings = Settings(edu_groups=(GROUP,), edu_request_delay_seconds=0)
    transport = RpcTransport()

    @asynccontextmanager
    async def factory():
        yield transport

    app = create_app(settings, transport_factory=factory)
    with TestClient(app) as client:
        groups = client.get('/api/groups').json()
        assert groups['groups'][0]['id'] == GROUP
        response = client.get('/api/schedule', params={'group_id': GROUP, 'start': '2026-09-07', 'end': '2026-09-20'})
        assert response.status_code == 200
        data = response.json()
        assert data['lessons'] and data['revision'] == groups['revision']
        assert all(set(l) == {'id', 'group_id', 'date', 'start_time', 'end_time', 'subject', 'lesson_type', 'teachers', 'rooms', 'subgroup_ids', 'subgroup_label', 'notes', 'warnings', 'evidence'} for l in data['lessons'])
        assert client.get('/api/catalog').status_code == 404
        assert client.get('/api/schedule', params={'group_id': GROUP, 'start': '2026-09-20', 'end': '2026-09-07'}).status_code == 422
        before = len(transport.calls)
        assert client.get('/api/schedule', params={'group_id': GROUP, 'start': '2026-09-07', 'end': '2026-09-12'}).status_code == 200
        assert len(transport.calls) == before


def test_live_edu_unknown_group_and_upstream_failure():
    settings = Settings(edu_groups=(GROUP,), edu_request_delay_seconds=0)

    @asynccontextmanager
    async def ok_factory():
        yield RpcTransport()

    app = create_app(settings, transport_factory=ok_factory)
    with TestClient(app) as client:
        empty = client.get('/api/schedule', params={'group_id': 'NOPE', 'start': '2026-09-07', 'end': '2026-09-12'}).json()
        assert empty['group'] is None and empty['lessons'] == [] and empty['available_dates'] == []

    @asynccontextmanager
    async def bad_factory():
        yield RpcTransport(failure='rpc')

    broken = create_app(settings, transport_factory=bad_factory)
    with TestClient(broken) as client:
        assert client.get('/api/schedule', params={'group_id': GROUP, 'start': '2026-09-07', 'end': '2026-09-12'}).status_code == 502


@pytest.mark.parametrize('failure', ['http', 'oversize', 'timeout'])
def test_http_transport_failures(failure):
    def handler(request):
        if failure == 'timeout':
            raise httpx.ReadTimeout('Timeout', request=request)
        return httpx.Response(503 if failure == 'http' else 200, content=b'x' * 2048)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with HttpTransport(Settings(max_download_bytes=1024), client=client) as transport:
                with pytest.raises((httpx.HTTPError, ValueError)):
                    await transport.request('GET', 'https://example.test')
    asyncio.run(run())


def test_duplicate_calendar_entry_keeps_all_provenance():
    first = Lesson(id='one', group_id=GROUP, date=WINDOW.start, subject='Math',
                   evidence=[Evidence(url='https://example.test', label='cell', raw_text='Math')])
    second = first.model_copy(update={'evidence': [Evidence(url='https://other.test', label='other cell', raw_text='Math')]})
    merged = merge_duplicates([first, first, second])
    assert len(merged) == 1
    assert len(merged[0].evidence) == 2
    with pytest.raises(ValueError, match='Conflicting'):
        merge_duplicates([first, first.model_copy(update={'subject': 'Different'})])


def test_snapshot_rejects_lesson_outside_coverage():
    from app.domain import Coverage
    with pytest.raises(ValueError):
        Snapshot(
            source=SourceInfo(id='edu_api', label='x', url='https://example.test', basis='dated'),
            coverage=Coverage(start=WINDOW.start, end=WINDOW.end),
            groups=[Group(id=GROUP, name=GROUP)],
            lessons=[Lesson(id='one', group_id=GROUP, date=date(2027, 1, 1), subject='Math',
                            evidence=[Evidence(url='https://example.test', label='cell', raw_text='Math')])],
        )
