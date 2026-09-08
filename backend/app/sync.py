import asyncio
import logging
from datetime import datetime, timezone

from .ports import ScheduleRepository, ScheduleSource

logger = logging.getLogger(__name__)


class Synchronizer:
    def __init__(self, repository: ScheduleRepository, source: ScheduleSource, settings, transport_factory):
        self.repository, self.source, self.settings = repository, source, settings
        self.transport_factory = transport_factory
        self._lock = None

    @property
    def updating(self):
        return self._lock is not None and self._lock.locked()

    async def run_once(self, transport=None, window=None):
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            timestamp = datetime.now(timezone.utc).isoformat()
            try:
                window = window or self.settings.window()
                if transport is None:
                    async with self.transport_factory() as owned:
                        snapshot = await self.source.fetch(owned, window)
                else:
                    snapshot = await self.source.fetch(transport, window)
                await asyncio.to_thread(self.repository.replace, snapshot, datetime.now(timezone.utc).isoformat())
                logger.info('Imported %d calendar entries for %d groups from %s', len(snapshot.lessons), len(snapshot.groups), snapshot.source.id)
                return True
            except Exception:
                logger.exception('Schedule update failed; previous snapshot retained')
                # Keep upstream response bodies, tokens and URLs out of the public API.
                await asyncio.to_thread(self.repository.failure, timestamp, 'Не удалось обновить расписание. Последняя успешная версия сохранена.')
                return False

    async def loop(self):
        while True:
            await self.run_once()
            await asyncio.sleep(self.settings.update_interval_seconds)
