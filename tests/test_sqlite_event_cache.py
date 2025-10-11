# -*- coding: utf-8 -*-
"""Tests ensuring SQLite event cache subscribers receive remote events."""

import asyncio
import contextlib

import pytest

from freeadmin.core.cache import SQLiteEventCache


@pytest.mark.asyncio
async def test_sqlite_event_cache_cross_instance(tmp_path) -> None:
    """Ensure events published via a separate cache instance are received."""

    db_path = tmp_path / "events.db"
    cache_a = SQLiteEventCache(path=str(db_path), poll_timeout=0.1)
    cache_b = SQLiteEventCache(path=str(db_path), poll_timeout=0.1)
    subscriber = await cache_a.subscribe("alpha")
    results: list[str] = []

    async def consume() -> None:
        async for payload in subscriber:
            results.append(payload)
            if len(results) == 2:
                break

    task = asyncio.create_task(consume())
    try:
        await asyncio.sleep(0)
        await cache_b.publish("alpha", "first")
        await cache_b.publish("alpha", "second")
        await asyncio.wait_for(task, timeout=2)
    finally:
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        cache_a.reconfigure()
        cache_b.reconfigure()

    assert results == ["first", "second"]


@pytest.mark.asyncio
async def test_sqlite_event_cache_polling_timeout(tmp_path) -> None:
    """Ensure polling detects remote events when no local notification occurs."""

    db_path = tmp_path / "polling.db"
    cache_a = SQLiteEventCache(path=str(db_path), poll_timeout=0.1)
    cache_b = SQLiteEventCache(path=str(db_path), poll_timeout=0.1)
    subscriber = await cache_a.subscribe("beta")
    received: list[str] = []

    async def consume() -> None:
        async for payload in subscriber:
            received.append(payload)
            break

    async def publish_later() -> None:
        await asyncio.sleep(cache_a.poll_timeout * 2)
        await cache_b.publish("beta", "remote")

    consumer = asyncio.create_task(consume())
    publisher = asyncio.create_task(publish_later())
    try:
        await asyncio.wait_for(asyncio.gather(consumer, publisher), timeout=3)
    finally:
        for task in (consumer, publisher):
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        cache_a.reconfigure()
        cache_b.reconfigure()

    assert received == ["remote"]


# The End
