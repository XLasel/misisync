"""Versioned integration boundary. nginx authenticates mTLS; a private header binds that proxy."""
from typing import Optional
import hashlib
import secrets
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.security import APIKeyHeader
from .academic import AcademicWeek, weeks
from .domain import Model, Schedule, Window
from .ports import SourceBusy

proxy_key = APIKeyHeader(name='X-Integration-Key', auto_error=False)

async def authenticated(request: Request, key: Optional[str] = Depends(proxy_key)):
    expected = request.app.state.settings.integration_proxy_secret
    if not expected or not key or not secrets.compare_digest(key, expected):
        raise HTTPException(403, 'Client certificate required')

router = APIRouter(prefix='/api/v1', tags=['Integration'], dependencies=[Depends(authenticated)])

class SchedulePage(Schedule):
    academic_weeks: list[AcademicWeek]
    timezone: str = 'Europe/Moscow'
    total: int
    offset: int
    limit: int
    next_offset: Optional[int]
    snapshot: str

@router.get('/schedule', response_model=SchedulePage, responses={
    404: {'description': 'Unknown group'},
    403: {'description': 'Client certificate required'},
    409: {'description': 'Snapshot changed; restart pagination'},
    422: {'description': 'Invalid parameters; maximum range 31 days'},
    429: {'description': 'Rate limited by gateway'},
    502: {'description': 'Upstream unavailable'},
    503: {'description': 'Upstream busy; retry after 5 seconds'},
})
async def schedule(request: Request, response: Response,
                   group_id: str = Query(min_length=1, max_length=100),
                   start: date = Query(), end: date = Query(),
                   subgroup: Optional[int] = Query(default=None, ge=1),
                   limit: int = Query(default=50, ge=1, le=100),
                   offset: int = Query(default=0, ge=0, le=10000),
                   snapshot: Optional[str] = Query(default=None, min_length=64, max_length=64)):
    if end < start or (end-start).days > 30:
        raise HTTPException(422, 'Range must be ordered and at most 31 days')
    if offset and snapshot is None:
        raise HTTPException(422, 'snapshot is required after the first page')
    try:
        result = await request.app.state.provider.schedule(group_id, Window(start=start, end=end))
    except SourceBusy:
        raise HTTPException(503, 'Upstream busy', headers={'Retry-After': '5'}) from None
    except Exception:
        raise HTTPException(502, 'Upstream unavailable') from None
    if result.group is None:
        raise HTTPException(404, 'Unknown group')
    lessons = sorted((l for l in result.lessons if subgroup is None or not l.subgroup_ids or subgroup in l.subgroup_ids),
                     key=lambda l: (l.date, l.start_time or '99:99', l.id))
    # Bind pagination to data AND query. No database or pagination-session storage needed.
    digest = hashlib.sha256((f'{group_id}|{start}|{end}|{subgroup}|' +
        result.model_dump_json(exclude={'fetched_at', 'stale', 'academic_weeks'})).encode()).hexdigest()
    if snapshot is not None and snapshot != digest:
        raise HTTPException(409, 'Snapshot changed; restart pagination')
    response.headers['Cache-Control'] = 'no-store'
    data = result.model_dump(exclude={'lessons', 'academic_weeks'})
    return SchedulePage(**data, lessons=lessons[offset:offset+limit],
        academic_weeks=weeks(result.window, request.app.state.settings), total=len(lessons),
        offset=offset, limit=limit, next_offset=offset+limit if offset+limit < len(lessons) else None,
        snapshot=digest)
