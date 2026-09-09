import asyncio
from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.composition import TransportPool
from app.config import Settings
from app.domain import Window
from app.ports import SourceBusy
from app.sources.edu.live import EduLiveService
from test_calendar import GROUP, RpcTransport

WEEK = Window(start=date(2026, 9, 7), end=date(2026, 9, 12))
NEXT = Window(start=date(2026, 9, 14), end=date(2026, 9, 19))


def service(**overrides):
    now = [0.0]
    transport = RpcTransport()

    @asynccontextmanager
    async def factory():
        yield transport

    settings = Settings(**dict(dict(edu_request_delay_seconds=0, edu_schedule_ttl_seconds=10,
                                   edu_stale_if_error_seconds=20, edu_retry_backoff_seconds=5), **overrides))
    return EduLiveService(settings, factory, clock=lambda: now[0]), transport, now


@pytest.mark.parametrize('empty', [False, True])
def test_expired_week_survives_error_with_original_timestamp_and_bounded_grace(empty):
    async def run():
        live, transport, now = service()
        transport.empty = empty
        original = await live.schedule(GROUP, WEEK)
        assert original.fetched_at and not original.stale
        transport.failure = 'rpc'
        now[0] = 11
        fallback = await live.schedule(GROUP, WEEK)
        assert fallback.lessons == original.lessons
        assert fallback.fetched_at == original.fetched_at
        assert fallback.stale and fallback.warnings
        count = len(transport.calls)
        now[0] = 12
        assert (await live.schedule(GROUP, WEEK)).stale
        assert len(transport.calls) == count  # failure backoff
        now[0] = 31
        with pytest.raises(ValueError):
            await live.schedule(GROUP, WEEK)
        transport.failure = None
        now[0] = 37
        assert not (await live.schedule(GROUP, WEEK)).stale
        await live.aclose()
    asyncio.run(run())


def test_ttl_starts_after_response_and_cache_is_reused():
    async def run():
        live, transport, now = service()
        original = live.source.fetch_week

        async def slow(*args):
            now[0] = 100
            return await original(*args)

        live.source.fetch_week = slow
        await live.schedule(GROUP, WEEK)
        count = len(transport.calls)
        now[0] = 105
        await live.schedule(GROUP, WEEK)
        assert len(transport.calls) == count
    asyncio.run(run())


def test_shared_request_survives_one_disconnected_visitor_and_caps_pending_work():
    async def run():
        live, _, _ = service(edu_max_pending_requests=1)
        await live.catalog()
        started, release = asyncio.Event(), asyncio.Event()
        calls = []

        async def fetch(*args):
            calls.append(args)
            started.set()
            await release.wait()
            return []

        live.source.fetch_week = fetch
        first = asyncio.create_task(live.schedule(GROUP, WEEK))
        await started.wait()
        second = asyncio.create_task(live.schedule(GROUP, WEEK))
        await asyncio.sleep(0)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        with pytest.raises(SourceBusy):
            await live.schedule(GROUP, NEXT)
        release.set()
        assert (await second).lessons == []
        assert len(calls) == 1 and not live._week_flights
        await live.aclose()
    asyncio.run(run())


def test_failed_requests_clean_up_and_back_off_without_old_data():
    async def run():
        live, transport, now = service(edu_schedule_cache_max_entries=1)
        transport.failure = 'rpc'
        for window in (WEEK, NEXT):
            with pytest.raises(ValueError):
                await live.schedule(GROUP, window)
            assert not live._week_flights
        count = len(transport.calls)
        with pytest.raises(ValueError):
            await live.schedule(GROUP, NEXT)
        assert len(transport.calls) == count and len(live._week_cache) == 1
        now[0] = 6
        transport.failure = None
        assert (await live.schedule(GROUP, NEXT)).lessons
    asyncio.run(run())


def test_catalog_outage_backoff_grace_and_observational_status():
    async def run():
        live, transport, now = service(edu_catalog_ttl_seconds=10)
        assert (await live.status()).last_success is None
        assert not transport.calls
        original = await live.catalog()
        failing = AsyncMock(side_effect=ValueError('unavailable'))
        live.source.load_catalog = failing
        now[0] = 11
        assert (await live.catalog()) == original
        assert (await live.status()).last_error
        now[0] = 12
        assert (await live.catalog()) == original
        assert failing.await_count == 1
        now[0] = 31
        with pytest.raises(ValueError):
            await live.catalog()
        with pytest.raises(ValueError):
            await live.catalog()
        assert failing.await_count == 2
    asyncio.run(run())


def test_initial_catalog_failure_is_not_retried_by_every_waiter():
    async def run():
        live, _, _ = service()
        failing = AsyncMock(side_effect=ValueError('unavailable'))
        live.source.load_catalog = failing
        results = await asyncio.gather(*(live.catalog() for _ in range(10)), return_exceptions=True)
        assert all(isinstance(result, ValueError) for result in results)
        assert failing.await_count == 1
    asyncio.run(run())


def test_sunday_has_no_upstream_schedule_request():
    async def run():
        live, transport, _ = service()
        result = await live.schedule(GROUP, Window(start=date(2026, 9, 13), end=date(2026, 9, 13)))
        assert result.available_dates == result.lessons == []
        assert len(transport.calls) == 1  # catalog only
    asyncio.run(run())


def test_cache_uses_upstream_identity_after_catalog_refresh():
    async def run():
        live, _, now = service(edu_catalog_ttl_seconds=1)
        await live.schedule(GROUP, WEEK)
        group = live._upstream[GROUP].model_copy(update={'id': 'new-id'})
        live.source.load_catalog = AsyncMock(return_value=[group])
        live.source.fetch_week = AsyncMock(return_value=[])
        now[0] = 2
        assert (await live.schedule(GROUP, WEEK)).lessons == []
        live.source.fetch_week.assert_awaited_once()
    asyncio.run(run())


def test_shutdown_cancels_background_loads_and_closes_transport(monkeypatch):
    async def run():
        live, _, _ = service()
        await live.catalog()
        started = asyncio.Event()

        async def wait(*args):
            started.set()
            await asyncio.Event().wait()

        live.source.fetch_week = wait
        caller = asyncio.create_task(live.schedule(GROUP, WEEK))
        await started.wait()
        await live.aclose()
        with pytest.raises(asyncio.CancelledError):
            await caller
        assert not live._week_flights

        transport = AsyncMock()
        monkeypatch.setattr('app.transports.http.HttpTransport', lambda settings: transport)
        pool = TransportPool(Settings(edu_max_concurrent_requests=1))
        async with pool() as first:
            assert first is transport
            waiting = asyncio.create_task(use_pool(pool))
            await asyncio.sleep(0)
            assert not waiting.done()
        assert await waiting is transport
        await pool.aclose()
        transport.__aexit__.assert_awaited_once()

    async def use_pool(pool):
        async with pool() as transport:
            return transport

    asyncio.run(run())
