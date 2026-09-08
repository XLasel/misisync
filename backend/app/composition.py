"""Composition root: wire the active schedule provider here when adding backends."""


def build_transport_factory(settings):
    from contextlib import asynccontextmanager
    from .transports.http import HttpTransport

    @asynccontextmanager
    async def factory():
        async with HttpTransport(settings) as transport:
            yield transport
    return factory


def build_provider(settings, transport_factory=None):
    """Return the active ScheduleProvider. Add new backends as explicit branches."""
    from .sources.edu.live import EduLiveService
    return EduLiveService(settings, transport_factory or build_transport_factory(settings))
