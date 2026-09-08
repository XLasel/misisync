import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from datetime import date

from fastapi import FastAPI, HTTPException, Query

from .composition import build_source, build_transport_factory, build_repository
from .config import Settings
from .domain import Catalog, Schedule, Status, Window
from .sync import Synchronizer

logging.basicConfig(level=logging.INFO)


def create_app(settings=None, *, source=None, repository=None, transport_factory=None):
    config = settings or Settings.from_env()
    repository = repository or build_repository(config)
    source = source or build_source(config)
    synchronizer = Synchronizer(repository, source, config, transport_factory or build_transport_factory(config))

    @asynccontextmanager
    async def lifespan(app):
        repository.initialize()
        task = asyncio.create_task(synchronizer.loop()) if config.enable_scheduler else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(title='Misisync API', version='2.0.0', lifespan=lifespan)
    app.state.repository = repository
    app.state.synchronizer = synchronizer

    @app.get('/api/health')
    def health():
        repository.status()
        return {'status': 'ok'}

    @app.get('/api/status', response_model=Status)
    def status():
        return repository.status().model_copy(update={'configured_source': source.info.id, 'updating': synchronizer.updating})

    @app.get('/api/groups', response_model=Catalog)
    def groups():
        return repository.catalog()

    @app.get('/api/schedule', response_model=Schedule)
    def schedule(group_id: str = Query(min_length=1, max_length=100),
                 start: date = Query(), end: date = Query()):
        if end < start or (end - start).days > 90:
            raise HTTPException(422, 'Requested date range must be ordered and at most 91 days')
        return repository.schedule(group_id, Window(start=start, end=end))

    return app


app = create_app()
