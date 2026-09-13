from datetime import date
from fastapi.testclient import TestClient
from app.academic import weeks
from app.config import Settings
from app.domain import Schedule, Window, Group, Lesson, Evidence
from app.main import create_app

KEY = 'a' * 64

class Provider:
    calls = 0
    changed = False
    async def schedule(self, group_id, window):
        self.calls += 1
        return Schedule(revision='v2' if self.changed else 'v1', group=Group(id=group_id, name='Test'),
            source=None, coverage=None, window=window, available_dates=[window.start], warnings=[],
            fetched_at='2026-09-11T12:00:00Z', lessons=[Lesson(id=str(i), group_id=group_id,
            date=window.start, subject='Test', subgroup_ids=[i] if i else [],
            evidence=[Evidence(url='https://edu.misis.ru/schedule', label='source', raw_text='Test')]) for i in range(3)])


def test_parity_around_anchor_and_year_boundary():
    s = Settings()
    result = weeks(Window(start=date(2026, 8, 31), end=date(2026, 9, 27)), s)
    assert [w.kind for w in result] == ['upper', 'lower', 'upper', 'lower']
    result = weeks(Window(start=date(2026, 12, 28), end=date(2027, 1, 10)),
                   Settings(academic_reference_date=date(2026, 12, 28), academic_reference_kind='upper'))
    assert [w.kind for w in result] == ['upper', 'lower']
    assert all(w.estimated for w in result)


def test_auth_pagination_filter_and_snapshot_change():
    provider = Provider()
    client = TestClient(create_app(Settings(integration_proxy_secret=KEY), provider=provider))
    query = {'group_id': '42', 'start': '2026-09-07', 'end': '2026-09-13', 'limit': 1}
    assert client.get('/api/v1/schedule', params=query).status_code == 403
    assert provider.calls == 0
    headers = {'X-Integration-Key': KEY}
    first = client.get('/api/v1/schedule', params=query, headers=headers)
    assert first.status_code == 200
    data = first.json()
    assert data['total'] == 3 and data['next_offset'] == 1
    assert data['academic_weeks'][0]['kind'] == 'lower'
    assert client.get('/api/v1/schedule', params={**query, 'offset': 1}, headers=headers).status_code == 422
    page = client.get('/api/v1/schedule', params={**query, 'offset': 1, 'snapshot': data['snapshot']}, headers=headers)
    assert page.json()['lessons'][0]['id'] == '1'
    filtered = client.get('/api/v1/schedule', params={**query, 'subgroup': 2, 'limit': 100}, headers=headers)
    assert [l['id'] for l in filtered.json()['lessons']] == ['0', '2']
    provider.changed = True
    assert client.get('/api/v1/schedule', params={**query, 'offset': 1, 'snapshot': data['snapshot']}, headers=headers).status_code == 409
    assert client.get('/api/v1/schedule', params={**query, 'end': '2027-01-01'}, headers=headers).status_code == 422


def test_public_schedule_has_same_server_estimate_and_disabled_integration_fails_closed():
    client = TestClient(create_app(Settings(), provider=Provider()))
    params = {'group_id': '42', 'start': '2026-09-14', 'end': '2026-09-20'}
    assert client.get('/api/schedule', params=params).json()['academic_weeks'][0]['kind'] == 'upper'
    assert client.get('/api/v1/schedule', params=params, headers={'X-Integration-Key': KEY}).status_code == 403
