"""Composition root: wire the active schedule provider here when adding backends."""


def build_transport_factory(settings):
    """Reuse one HttpTransport for the process lifetime (connection pooling)."""
    from contextlib import asynccontextmanager
    from .transports.http import HttpTransport

    state = {'transport': None}

    @asynccontextmanager
    async def factory():
        if state['transport'] is None:
            transport = HttpTransport(settings)
            await transport.__aenter__()
            state['transport'] = transport
        yield state['transport']
    return factory


def build_provider(settings, transport_factory=None):
    """Return the active ScheduleProvider. Add new backends as explicit branches."""
    from .sources.edu.live import EduLiveService
    return EduLiveService(settings, transport_factory or build_transport_factory(settings))
