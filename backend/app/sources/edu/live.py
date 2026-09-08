"""On-demand edu.misis.ru access: catalog + per-week schedule with short in-memory TTL."""
import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

from ...domain import Catalog, Coverage, Schedule, Status, Window, merge_duplicates
from .source import EduApiSource

logger = logging.getLogger(__name__)


class EduLiveService:
    def __init__(self, settings, transport_factory):
        self.settings = settings
        self.transport_factory = transport_factory
        self.source = EduApiSource(settings)
        self._catalog_lock = None
        self._catalog_expires = 0.0
        self._catalog_revision = None
        self._catalog_fetched_at = None
        self._catalog_error = None
        self._upstream = {}
        self._groups = []
        self._week_cache = {}
        self._week_lock = None

    @property
    def info(self):
        return self.source.info

    async def warm_catalog(self):
        try:
            await self.catalog()
        except Exception:
            logger.exception('Initial edu catalog warm-up failed; will retry on first request')

    async def catalog(self) -> Catalog:
        await self._ensure_catalog()
        return Catalog(revision=self._catalog_revision, groups=list(self._groups))

    async def status(self) -> Status:
        try:
            await self._ensure_catalog()
        except Exception:
            pass
        return Status(source=self.info, coverage=None, revision=self._catalog_revision,
                      last_success=self._catalog_fetched_at, last_attempt=self._catalog_fetched_at,
                      last_error=self._catalog_error, warnings=[],
                      group_count=len(self._groups), lesson_count=0, configured_source=self.info.id)

    async def schedule(self, group_id: str, window: Window) -> Schedule:
        await self._ensure_catalog()
        edu_group = self._upstream.get(group_id)
        if edu_group is None:
            return Schedule(revision=self._catalog_revision, group=None, source=self.info, coverage=None,
                            window=window, available_dates=[], lessons=[], warnings=[])
        coverage = Coverage(start=window.start, end=window.end, weekdays=list(range(6)))
        lessons = []
        for monday in self.source.week_mondays(window):
            lessons.extend(await self._week_lessons(edu_group, monday, window))
        lessons = merge_duplicates(lessons)
        group = self.source.domain_group(edu_group, lessons)
        return Schedule(revision=self._catalog_revision, group=group, source=self.info, coverage=coverage,
                        window=window, available_dates=[d for d in window.dates() if coverage.includes(d)],
                        lessons=lessons, warnings=[])

    def _lock(self, attr):
        if getattr(self, attr) is None:
            setattr(self, attr, asyncio.Lock())
        return getattr(self, attr)

    async def _ensure_catalog(self):
        if self._groups and time.monotonic() < self._catalog_expires:
            return
        async with self._lock('_catalog_lock'):
            if self._groups and time.monotonic() < self._catalog_expires:
                return
            try:
                async with self.transport_factory() as transport:
                    upstream = await self.source.load_catalog(transport)
                self._upstream = {g.name: g for g in upstream}
                self._groups = [self.source.domain_group(g) for g in upstream]
                self._catalog_revision = uuid.uuid4().hex
                self._catalog_fetched_at = datetime.now(timezone.utc).isoformat()
                self._catalog_expires = time.monotonic() + self.settings.edu_catalog_ttl_seconds
                self._catalog_error = None
            except Exception:
                self._catalog_error = 'Не удалось загрузить список групп из электронного расписания.'
                logger.exception('edu catalog refresh failed')
                if self._groups:
                    return
                raise

    async def _week_lessons(self, edu_group, monday, window: Window):
        key = (edu_group.name, monday.isoformat())
        cached = self._week_cache.get(key)
        if cached and time.monotonic() < cached[0]:
            return [lesson for lesson in cached[1] if window.start <= lesson.date <= window.end]
        async with self._lock('_week_lock'):
            cached = self._week_cache.get(key)
            if cached and time.monotonic() < cached[0]:
                return [lesson for lesson in cached[1] if window.start <= lesson.date <= window.end]
            full = Window(start=monday, end=monday + timedelta(days=5))
            async with self.transport_factory() as transport:
                lessons = await self.source.fetch_week(transport, edu_group, monday, full)
            self._week_cache[key] = (time.monotonic() + self.settings.edu_schedule_ttl_seconds, lessons)
            return [lesson for lesson in lessons if window.start <= lesson.date <= window.end]
