"""On-demand calendar with bounded caching, single-flight loads and stale-on-error fallback."""
import asyncio
import logging
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from ...domain import Catalog, Coverage, Lesson, Schedule, Status, Window, merge_duplicates
from ...ports import SourceBusy
from .source import EduApiSource

logger = logging.getLogger(__name__)


@dataclass
class WeekEntry:
    lessons: Optional[list[Lesson]]
    fetched_at: Optional[str]
    expires: float
    stale_until: float
    retry_at: float = 0
    error: bool = False


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class EduLiveService:
    def __init__(self, settings, transport_factory, *, clock=time.monotonic):
        self.settings, self.transport_factory, self.clock = settings, transport_factory, clock
        self.source = EduApiSource(settings)
        self._catalog_lock = None
        self._catalog_expires = self._catalog_retry_at = self._catalog_stale_until = 0.0
        self._catalog_revision = self._catalog_fetched_at = self._catalog_attempted_at = None
        self._catalog_error = None
        self._upstream, self._groups = {}, []
        self._week_cache = OrderedDict()
        self._week_flights = {}
        self._closed = False

    @property
    def info(self):
        return self.source.info

    async def warm_catalog(self):
        try:
            await self.catalog()
        except Exception:
            logger.warning('Initial catalog unavailable; later requests will retry after backoff')

    async def aclose(self):
        self._closed = True
        tasks = list(self._week_flights.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._week_flights.clear()

    async def catalog(self) -> Catalog:
        await self._ensure_catalog()
        return Catalog(revision=self._catalog_revision, groups=list(self._groups))

    async def status(self) -> Status:
        # Status is observational: polling it must not initiate upstream work.
        return Status(source=self.info, revision=self._catalog_revision,
                      last_success=self._catalog_fetched_at, last_attempt=self._catalog_attempted_at,
                      last_error=self._catalog_error, group_count=len(self._groups),
                      lesson_count=sum(len(e.lessons or []) for e in self._week_cache.values()),
                      configured_source=self.info.id, updating=bool(self._week_flights))

    async def schedule(self, group_id: str, window: Window) -> Schedule:
        await self._ensure_catalog()
        edu_group = self._upstream.get(group_id)
        revision = self._catalog_revision
        if edu_group is None:
            return Schedule(revision=revision, group=None, source=self.info, coverage=None,
                            window=window, available_dates=[], lessons=[], warnings=[])
        coverage = Coverage(start=window.start, end=window.end, weekdays=list(range(6)))
        lessons, entries = [], []
        for monday in self.source.week_mondays(window):
            if monday + timedelta(days=5) < window.start:
                continue  # A Sunday-only request has no covered dates.
            entry = await self._week_entry(edu_group, monday)
            entries.append(entry)
            lessons.extend(l for l in entry.lessons or [] if window.start <= l.date <= window.end)
        stale = any(e.error for e in entries)
        warnings = []
        if stale:
            warnings.append('Не удалось обновить расписание университета. Показана последняя полученная версия из кэша.')
        if self._catalog_error:
            warnings.append('Список групп временно доступен из кэша: университет не ответил на обновление.')
        timestamps = [e.fetched_at for e in entries if e.fetched_at]
        return Schedule(revision=revision, group=self.source.domain_group(edu_group, lessons),
                        source=self.info, coverage=coverage, window=window,
                        available_dates=[d for d in window.dates() if coverage.includes(d)],
                        lessons=merge_duplicates(lessons), warnings=warnings,
                        fetched_at=min(timestamps) if timestamps else None, stale=stale)

    async def _ensure_catalog(self):
        if self._catalog_lock is None:
            self._catalog_lock = asyncio.Lock()
        async with self._catalog_lock:
            now = self.clock()
            if self._groups and now < self._catalog_expires:
                return
            if now < self._catalog_retry_at:
                if self._groups and now < self._catalog_stale_until:
                    return
                raise ValueError('Catalog temporarily unavailable')
            self._catalog_attempted_at = utc_now()
            try:
                async with self.transport_factory() as transport:
                    upstream = await self.source.load_catalog(transport)
                self._upstream = {g.name: g for g in upstream}
                self._groups = [self.source.domain_group(g) for g in upstream]
                self._catalog_revision = uuid.uuid4().hex
                self._catalog_fetched_at = utc_now()
                self._catalog_expires = self.clock() + self.settings.edu_catalog_ttl_seconds
                self._catalog_stale_until = self._catalog_expires + self.settings.edu_stale_if_error_seconds
                self._catalog_error = None
                self._catalog_retry_at = 0
            except Exception:
                self._catalog_error = 'Не удалось обновить список групп университета.'
                self._catalog_retry_at = self.clock() + self.settings.edu_retry_backoff_seconds
                logger.exception('edu catalog refresh failed')
                if self._groups and self.clock() < self._catalog_stale_until:
                    return
                raise

    async def _week_entry(self, group, monday):
        if self._closed:
            raise SourceBusy('Service shutting down')
        # Names can survive an upstream ID change. Cache by the actual upstream identity.
        key = (group.id, monday.isoformat())
        now = self.clock()
        cached = self._week_cache.get(key)
        if cached:
            self._week_cache.move_to_end(key)
            if now < cached.expires or now < cached.retry_at:
                if cached.lessons is not None and (not cached.error or now < cached.stale_until):
                    return cached
                raise ValueError('Schedule temporarily unavailable')
        task = self._week_flights.get(key)
        if task is None:
            if len(self._week_flights) >= self.settings.edu_max_pending_requests:
                raise SourceBusy('Too many distinct upstream requests')
            task = asyncio.create_task(self._load_week(key, group, monday, cached))
            self._week_flights[key] = task
            def finished(done):
                if self._week_flights.get(key) is done:
                    self._week_flights.pop(key, None)
                if not done.cancelled():
                    done.exception()  # Observe failures even if all requesters disconnected.
            task.add_done_callback(finished)
        # Cancelling one browser request must not cancel work shared with other visitors.
        return await asyncio.shield(task)

    async def _load_week(self, key, group, monday, previous):
        try:
            full = Window(start=monday, end=monday + timedelta(days=5))
            async with self.transport_factory() as transport:
                lessons = await self.source.fetch_week(transport, group, monday, full)
            now = self.clock()  # TTL starts after the response, not before the network wait.
            expires = now + self.settings.edu_schedule_ttl_seconds
            entry = WeekEntry(lessons, utc_now(), expires, expires + self.settings.edu_stale_if_error_seconds)
        except Exception:
            logger.exception('edu week refresh failed')
            now = self.clock()
            usable = previous is not None and previous.lessons is not None and now < previous.stale_until
            entry = WeekEntry(previous.lessons if usable else None, previous.fetched_at if usable else None,
                              0, previous.stale_until if usable else 0,
                              retry_at=now + self.settings.edu_retry_backoff_seconds, error=True)
            self._store_week(key, entry)
            if not usable:
                raise
            return entry
        self._store_week(key, entry)
        return entry

    def _store_week(self, key, entry):
        self._week_cache[key] = entry
        self._week_cache.move_to_end(key)
        while len(self._week_cache) > self.settings.edu_schedule_cache_max_entries:
            self._week_cache.popitem(last=False)
