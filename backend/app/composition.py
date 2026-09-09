"""Create one connection pool owned and closed by the application lifespan."""
import asyncio
from contextlib import asynccontextmanager


class TransportPool:
    def __init__(self, settings):
        self.settings = settings
        self.transport = None
        self._gate = None

    @asynccontextmanager
    async def __call__(self):
        if self._gate is None:
            self._gate = asyncio.Semaphore(self.settings.edu_max_concurrent_requests)
        async with self._gate:
            if self.transport is None:
                from .transports.http import HttpTransport
                self.transport = HttpTransport(self.settings)
            yield self.transport

    async def aclose(self):
        if self.transport is not None:
            await self.transport.__aexit__(None, None, None)
            self.transport = None


def build_transport_factory(settings):
    return TransportPool(settings)


def build_provider(settings, transport_factory=None):
    from .sources.edu.live import EduLiveService
    return EduLiveService(settings, transport_factory or build_transport_factory(settings))
