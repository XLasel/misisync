import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from datetime import date

from fastapi import FastAPI, HTTPException, Query, Request

from .composition import build_provider, build_transport_factory
from .config import Settings, SlidingWindowRateLimiter
from .domain import Catalog, Schedule, Status, Window

logging.basicConfig(level=logging.INFO)


def create_app(settings=None, *, provider=None, transport_factory=None):
    config = settings or Settings.from_env()
    transport_factory = transport_factory or build_transport_factory(config)
    provider = provider or build_provider(config, transport_factory)
    limiter = SlidingWindowRateLimiter(config.schedule_rate_limit_per_minute)

    @asynccontextmanager
    async def lifespan(app):
        warm = asyncio.create_task(provider.warm_catalog()) if hasattr(provider, 'warm_catalog') else None
        try:
            yield
        finally:
            if warm:
                warm.cancel()
                with suppress(asyncio.CancelledError):
                    await warm

    app = FastAPI(title='Misisync API', version='2.0.0', lifespan=lifespan)
    app.state.provider = provider

    @app.get('/api/health')
    async def health():
        return {'status': 'ok'}

    @app.get('/api/status', response_model=Status)
    async def status():
        result = await provider.status()
        return result.model_copy(update={'configured_source': provider.info.id, 'updating': False})

    @app.get('/api/groups', response_model=Catalog)
    async def groups():
        try:
            return await provider.catalog()
        except Exception:
            raise HTTPException(502, 'Не удалось загрузить список групп из электронного расписания.') from None

    @app.get('/api/schedule', response_model=Schedule)
    async def schedule(request: Request, group_id: str = Query(min_length=1, max_length=100),
                       start: date = Query(), end: date = Query()):
        if end < start or (end - start).days > 90:
            raise HTTPException(422, 'Requested date range must be ordered and at most 91 days')
        client = request.client.host if request.client else 'unknown'
        if not limiter.allow(client):
            raise HTTPException(429, 'Слишком много запросов расписания. Подожди минуту и попробуй снова.')
        try:
            return await provider.schedule(group_id, Window(start=start, end=end))
        except Exception:
            raise HTTPException(502, 'Не удалось загрузить расписание из электронного расписания.') from None

    return app


app = create_app()
