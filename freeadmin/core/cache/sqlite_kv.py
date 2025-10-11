# -*- coding: utf-8 -*-
"""
sqlite_kv

Reusable SQLite-backed key/value cache with expiration support.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from threading import RLock
from typing import Iterable


class SQLiteKeyValueCache:
    """Persist key/value pairs with per-record expiration timestamps."""

    def __init__(
        self,
        path: str | None = None,
        *,
        table_name: str = "kv_cache",
    ) -> None:
        """Initialize the cache and prepare the SQLite schema."""

        self._path = path or ":memory:"
        self._table = self._validate_table(table_name)
        self._connection: sqlite3.Connection | None = None
        self._lock = RLock()
        self._connect()

    @property
    def path(self) -> str:
        """Return the SQLite database path used for persistence."""

        return self._path

    def set(self, key: str, payload: bytes, expires_at: datetime) -> None:
        """Store ``payload`` for ``key`` with the provided ``expires_at`` timestamp."""

        with self._lock:
            assert self._connection is not None
            self._connection.execute(
                f"""
                INSERT INTO {self._table}(key, payload, expires_at)
                VALUES(?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    payload=excluded.payload,
                    expires_at=excluded.expires_at
                """.strip(),
                (key, sqlite3.Binary(payload), expires_at.timestamp()),
            )
            self._connection.commit()

    def get(self, key: str) -> tuple[bytes, datetime] | None:
        """Return cached value for ``key`` if it exists and has not expired."""

        with self._lock:
            assert self._connection is not None
            cursor = self._connection.execute(
                f"SELECT payload, expires_at FROM {self._table} WHERE key = ?",
                (key,),
            )
            row = cursor.fetchone()
            cursor.close()
            if not row:
                return None
            payload, expires_ts = row
            expires_at = datetime.fromtimestamp(float(expires_ts))
            if expires_at <= datetime.now():
                self._connection.execute(
                    f"DELETE FROM {self._table} WHERE key = ?",
                    (key,),
                )
                self._connection.commit()
                return None
            return bytes(payload), expires_at

    def delete(self, key: str) -> None:
        """Remove cached value for ``key`` if present."""

        with self._lock:
            assert self._connection is not None
            self._connection.execute(
                f"DELETE FROM {self._table} WHERE key = ?",
                (key,),
            )
            self._connection.commit()

    def items(self) -> list[tuple[str, bytes, datetime]]:
        """Return all non-expired key/value pairs currently stored."""

        self.prune_expired()
        with self._lock:
            assert self._connection is not None
            cursor = self._connection.execute(
                f"SELECT key, payload, expires_at FROM {self._table}",
            )
            rows = cursor.fetchall()
            cursor.close()
        return [
            (key, bytes(payload), datetime.fromtimestamp(float(expires_ts)))
            for key, payload, expires_ts in rows
        ]

    def prune_expired(self) -> int:
        """Remove expired rows and return the number of deleted entries."""

        now = datetime.now().timestamp()
        with self._lock:
            assert self._connection is not None
            cursor = self._connection.execute(
                f"DELETE FROM {self._table} WHERE expires_at <= ?",
                (now,),
            )
            deleted = cursor.rowcount
            self._connection.commit()
        return int(deleted)

    def _connect(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
            self._connection = sqlite3.connect(self._path, check_same_thread=False)
            self._connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    key TEXT PRIMARY KEY,
                    payload BLOB NOT NULL,
                    expires_at REAL NOT NULL
                )
                """.strip()
            )
            self._connection.commit()

    def _validate_table(self, name: str) -> str:
        """Ensure ``name`` is safe for use as an SQLite identifier."""

        if not name or not all(ch.isalnum() or ch == "_" for ch in name):
            raise ValueError("Table name must contain only alphanumeric characters or underscores")
        return name


__all__: Iterable[str] = ["SQLiteKeyValueCache"]


# The End

