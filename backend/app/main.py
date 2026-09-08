import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import Optional

from fastapi import FastAPI, Query

from .config import Settings
from .db import Database
from .sync import Synchronizer

logging.basicConfig(level=logging.INFO)


def create_app(settings=None):
    config = settings or Settings.from_env()
    db = Database(config.database_path)
    synchronizer = Synchronizer(db, config)

    @asynccontextmanager
    async def lifespan(app):
        db.initialize()
        task = asyncio.create_task(synchronizer.loop()) if config.enable_scheduler else None
        yield
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title='Misisync API', version='1.0.0', lifespan=lifespan)
    app.state.db = db
    app.state.synchronizer = synchronizer

    @app.get('/api/health')
    def health():
        db.status()
        return {'status': 'ok'}

    @app.get('/api/status')
    def status():
        result = db.status()
        result['source_url'] = result['source_url'] or config.source_url
        result['updating'] = synchronizer.updating
        return result

    @app.get('/api/groups', response_model=list[str])
    def groups():
        return db.groups()

    @app.get('/api/catalog')
    def catalog():
        return db.catalog()

    @app.get('/api/schedule')
    def schedule(group: str = Query(default='', max_length=100), weekday: Optional[int] = Query(default=None, ge=0, le=6), subgroup: Optional[int] = Query(default=None, ge=1, le=99)):
        return db.schedule(group, weekday, subgroup) if group else []

    return app


app = create_app()
