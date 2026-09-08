"""Composition root: concrete adapters are selected and wired only here."""


def build_source(settings):
    if settings.schedule_source == 'excel':
        from .sources.excel.source import ExcelSource
        return ExcelSource(settings)
    if settings.schedule_source == 'edu_api':
        from .sources.edu.source import EduApiSource
        return EduApiSource(settings)
    raise ValueError('Unknown schedule source')


def build_transport_factory(settings):
    from contextlib import asynccontextmanager
    from .transports.http import HttpTransport

    @asynccontextmanager
    async def factory():
        async with HttpTransport(settings) as transport:
            yield transport
    return factory


def build_repository(settings):
    from .repositories.sqlite import Database
    return Database(settings.database_path)
