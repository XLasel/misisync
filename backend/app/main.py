import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from datetime import date

from fastapi import FastAPI, HTTPException, Query

from .composition import build_provider, build_transport_factory
from .config import Settings
from .academic import weeks
from .integration import router as integration_router
from .ports import SourceBusy
from .domain import Catalog, Schedule, Status, Window

logging.basicConfig(level=logging.INFO)


def create_app(settings=None, *, provider=None, transport_factory=None):
    config = settings or Settings.from_env()
    transport_factory = transport_factory or build_transport_factory(config)
    provider = provider or build_provider(config, transport_factory)

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
            if hasattr(provider, 'aclose'):
                await provider.aclose()
            if hasattr(transport_factory, 'aclose'):
                await transport_factory.aclose()

    app = FastAPI(title='Misisync API', version='2.0.0', lifespan=lifespan)
    app.state.provider = provider
    app.state.settings = config
    app.include_router(integration_router)

    @app.get('/api/health')
    async def health():
        return {'status': 'ok'}

    @app.get('/api/status', response_model=Status)
    async def status():
        result = await provider.status()
        return result

    @app.get('/api/groups', response_model=Catalog)
    async def groups():
        try:
            return await provider.catalog()
        except SourceBusy:
            raise HTTPException(503, 'Источник занят. Попробуй через несколько секунд.', headers={'Retry-After': '5'}) from None
        except Exception:
            raise HTTPException(502, 'Не удалось загрузить список групп из электронного расписания.') from None

    @app.get('/api/schedule', response_model=Schedule)
    async def schedule(group_id: str = Query(min_length=1, max_length=100),
                       start: date = Query(), end: date = Query()):
        if end < start or (end - start).days > 90:
            raise HTTPException(422, 'Requested date range must be ordered and at most 91 days')
        try:
            result = await provider.schedule(group_id, Window(start=start, end=end))
            return result.model_copy(update={'academic_weeks': weeks(result.window, config)})
        except SourceBusy:
            raise HTTPException(503, 'Источник занят. Попробуй через несколько секунд.', headers={'Retry-After': '5'}) from None
        except Exception:
            raise HTTPException(502, 'Не удалось загрузить расписание из электронного расписания.') from None

    return app


app = create_app()
