# -*- coding: utf-8 -*-
"""
sqlite

SQLite-backed event cache implementation for dashboard cards.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass
from threading import RLock
from typing import AsyncIterator, Dict, List, Tuple


@dataclass
class _SQLiteEvent:
    """Represent a persisted event payload fetched from SQLite."""

    event_id: int
    payload: str


class SQLiteEventCache:
    """Store and stream card events using a lightweight SQLite backend."""

    def __init__(
        self, path: str | None = None, *, poll_timeout: float = 0.5
    ) -> None:
        """Initialize the cache and configure its storage and polling interval."""

        self._path = path or ":memory:"
        self._connection: sqlite3.Connection | None = None
        self._connection_lock = RLock()
        self._channel_conditions: Dict[str, asyncio.Condition] = {}
        self._channel_versions: Dict[str, int] = {}
        self._poll_timeout = poll_timeout
        self._connect()

    @property
    def path(self) -> str:
        """Return the SQLite database path currently backing the cache."""

        return self._path

    @property
    def poll_timeout(self) -> float:
        """Return the timeout used for polling the SQLite database."""

        return self._poll_timeout

    async def publish(self, channel: str, payload: str) -> None:
        """Persist ``payload`` for ``channel`` and wake awaiting subscribers."""

        await asyncio.to_thread(self._insert_event, channel, payload)
        condition = self._get_condition(channel)
        async with condition:
            condition.notify_all()

    async def subscribe(self, channel: str) -> AsyncIterator[str]:
        """Return an asynchronous iterator yielding events for ``channel``."""

        last_id = await asyncio.to_thread(self._get_last_event_id, channel)
        return _SQLiteChannelSubscription(self, channel, last_id)

    def reconfigure(self, path: str | None = None) -> None:
        """Reconnect the cache using a new database ``path`` if provided."""

        target = path or ":memory:"
        if target == self._path and self._connection is not None:
            return
        self._path = target
        self._connect()

    def _connect(self) -> None:
        with self._connection_lock:
            if self._connection is not None:
                self._connection.close()
            self._connection = sqlite3.connect(self._path, check_same_thread=False)
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS card_events (
                    channel TEXT NOT NULL,
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
                )
                """.strip()
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS card_last_payload (
                    channel TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    serializer TEXT NOT NULL,
                    updated_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
                )
                """.strip()
            )
            self._connection.commit()
            cursor = self._connection.execute(
                "SELECT channel, MAX(id) FROM card_events GROUP BY channel"
            )
            rows = cursor.fetchall()
            cursor.close()
            self._channel_versions = {
                channel: int(last_id)
                for channel, last_id in rows
                if last_id is not None
            }

    def _get_condition(self, channel: str) -> asyncio.Condition:
        condition = self._channel_conditions.get(channel)
        if condition is None:
            condition = asyncio.Condition()
            self._channel_conditions[channel] = condition
        return condition

    def _insert_event(self, channel: str, payload: str) -> None:
        with self._connection_lock:
            assert self._connection is not None
            cursor = self._connection.execute(
                "INSERT INTO card_events(channel, payload) VALUES(?, ?)",
                (channel, payload),
            )
            self._connection.commit()
            self._channel_versions[channel] = int(cursor.lastrowid)

    def _get_last_event_id(self, channel: str) -> int:
        with self._connection_lock:
            assert self._connection is not None
            cursor = self._connection.execute(
                "SELECT id FROM card_events WHERE channel = ? ORDER BY id DESC LIMIT 1",
                (channel,),
            )
            row = cursor.fetchone()
            cursor.close()
        return int(row[0]) if row else 0

    def _query_channel_version(self, channel: str) -> int:
        with self._connection_lock:
            assert self._connection is not None
            cursor = self._connection.execute(
                "SELECT MAX(id) FROM card_events WHERE channel = ?",
                (channel,),
            )
            row = cursor.fetchone()
            cursor.close()
        version = int(row[0]) if row and row[0] is not None else 0
        self._channel_versions[channel] = max(
            version, self._channel_versions.get(channel, 0)
        )
        return self._channel_versions[channel]

    def _fetch_events(self, channel: str, last_id: int) -> List[_SQLiteEvent]:
        with self._connection_lock:
            assert self._connection is not None
            cursor = self._connection.execute(
                "SELECT id, payload FROM card_events WHERE channel = ? AND id > ? ORDER BY id ASC",
                (channel, last_id),
            )
            rows = cursor.fetchall()
            cursor.close()
        return [_SQLiteEvent(event_id=row[0], payload=row[1]) for row in rows]

    def store_last_payload(self, channel: str, payload: str, serializer: str) -> None:
        """Persist ``payload`` for ``channel`` using the provided ``serializer`` label."""

        with self._connection_lock:
            assert self._connection is not None
            self._connection.execute(
                """
                INSERT INTO card_last_payload(channel, payload, serializer)
                VALUES(?, ?, ?)
                ON CONFLICT(channel) DO UPDATE SET
                    payload=excluded.payload,
                    serializer=excluded.serializer,
                    updated_at=strftime('%s', 'now')
                """.strip(),
                (channel, payload, serializer),
            )
            self._connection.commit()

    def get_last_payload(self, channel: str) -> Tuple[str, str] | None:
        """Return the cached payload and serializer for ``channel`` if present."""

        with self._connection_lock:
            assert self._connection is not None
            cursor = self._connection.execute(
                "SELECT payload, serializer FROM card_last_payload WHERE channel = ?",
                (channel,),
            )
            row = cursor.fetchone()
            cursor.close()
        if row is None:
            return None
        return str(row[0]), str(row[1])

    def get_last_payloads(self) -> Dict[str, Tuple[str, str]]:
        """Return a mapping of channels to their cached payload and serializer."""

        with self._connection_lock:
            assert self._connection is not None
            cursor = self._connection.execute(
                "SELECT channel, payload, serializer FROM card_last_payload"
            )
            rows = cursor.fetchall()
            cursor.close()
        return {str(row[0]): (str(row[1]), str(row[2])) for row in rows}

    def _has_new_events(self, channel: str, last_id: int) -> bool:
        cached = self._channel_versions.get(channel, 0)
        if cached > last_id:
            return True
        latest = self._query_channel_version(channel)
        return latest > last_id


class _SQLiteChannelSubscription:
    """Iterate over events for a single channel."""

    def __init__(self, cache: SQLiteEventCache, channel: str, last_id: int) -> None:
        """Initialize the subscription state for ``channel``."""
        self._cache = cache
        self._channel = channel
        self._last_id = last_id

    def __aiter__(self) -> "_SQLiteChannelSubscription":
        """Return the asynchronous iterator instance."""
        return self

    async def __anext__(self) -> str:
        """Yield the next available payload for the subscription."""
        condition = self._cache._get_condition(self._channel)
        while True:
            payload = await self._poll_next_event()
            if payload is not None:
                return payload

            async with condition:
                payload = await self._poll_next_event()
                if payload is not None:
                    return payload
                try:
                    await asyncio.wait_for(
                        condition.wait_for(self._has_pending_local_events),
                        timeout=self._cache.poll_timeout,
                    )
                except asyncio.TimeoutError:
                    continue

    async def _poll_next_event(self) -> str | None:
        events = await asyncio.to_thread(
            self._cache._fetch_events, self._channel, self._last_id
        )
        if not events:
            return None
        return self._consume_event(events[0])

    def _has_pending_local_events(self) -> bool:
        cached = self._cache._channel_versions.get(self._channel, 0)
        return cached > self._last_id

    def _consume_event(self, event: _SQLiteEvent) -> str:
        self._last_id = event.event_id
        return event.payload

__all__ = ["SQLiteEventCache"]


# The End
