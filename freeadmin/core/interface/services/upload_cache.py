# -*- coding: utf-8 -*-
"""
upload_cache

SQLite-backed cache for temporary import uploads with TTL support.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Iterable, List, Tuple


class SQLiteKeyValueStore:
    """Persist simple key/value pairs with expiration metadata in SQLite."""

    def __init__(self, path: str | None = None, table: str = "kv_store") -> None:
        """Initialize the store backing file and table name."""

        self._path = path or ":memory:"
        self._table = table
        self._connection: sqlite3.Connection | None = None
        self._lock = RLock()
        self._connect()

    def _connect(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
            self._connection = sqlite3.connect(self._path, check_same_thread=False)
            self._connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
                """.strip()
            )
            self._connection.commit()

    def set(self, key: str, value: str, expires_at: datetime) -> None:
        """Store ``value`` for ``key`` with ``expires_at`` timestamp."""

        with self._lock:
            assert self._connection is not None
            self._connection.execute(
                f"""
                INSERT INTO {self._table} (key, value, expires_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    expires_at=excluded.expires_at
                """.strip(),
                (key, value, expires_at.timestamp()),
            )
            self._connection.commit()

    def _fetch_row(self, key: str) -> tuple[str, float] | None:
        with self._lock:
            assert self._connection is not None
            cursor = self._connection.execute(
                f"SELECT value, expires_at FROM {self._table} WHERE key = ?",
                (key,),
            )
            row = cursor.fetchone()
            cursor.close()
        if row is None:
            return None
        value, expires_at = row
        return str(value), float(expires_at)

    def get(self, key: str) -> tuple[str, datetime] | None:
        """Return the stored value and expiration for ``key`` if present."""

        row = self._fetch_row(key)
        if row is None:
            return None
        value, expires_at = row
        return value, datetime.fromtimestamp(expires_at)

    def delete(self, key: str) -> tuple[str, datetime] | None:
        """Remove ``key`` from the store returning its value if available."""

        record = self._fetch_row(key)
        if record is None:
            return None
        with self._lock:
            assert self._connection is not None
            self._connection.execute(
                f"DELETE FROM {self._table} WHERE key = ?",
                (key,),
            )
            self._connection.commit()
        value, expires_at = record
        return value, datetime.fromtimestamp(expires_at)

    def purge(self, before: datetime) -> List[Tuple[str, str, datetime]]:
        """Remove entries expiring before ``before`` returning purged rows."""

        with self._lock:
            assert self._connection is not None
            cursor = self._connection.execute(
                f"SELECT key, value, expires_at FROM {self._table} WHERE expires_at <= ?",
                (before.timestamp(),),
            )
            rows = cursor.fetchall()
            cursor.close()
            self._connection.executemany(
                f"DELETE FROM {self._table} WHERE key = ?",
                ((row[0],) for row in rows),
            )
            self._connection.commit()
        return [
            (str(key), str(value), datetime.fromtimestamp(float(expires)))
            for key, value, expires in rows
        ]

    def items(self) -> Iterable[Tuple[str, str, datetime]]:
        """Yield key/value pairs with their expiration timestamps."""

        with self._lock:
            assert self._connection is not None
            cursor = self._connection.execute(
                f"SELECT key, value, expires_at FROM {self._table}"
            )
            rows = cursor.fetchall()
            cursor.close()
        for key, value, expires in rows:
            yield (str(key), str(value), datetime.fromtimestamp(float(expires)))


@dataclass
class CachedUpload:
    path: Path
    fmt: str
    expires_at: datetime


class SQLiteUploadCache(SQLiteKeyValueStore):
    """Persist ``CachedUpload`` records in SQLite with TTL enforcement."""

    def __init__(self, path: str | None = None) -> None:
        """Initialize the cache optionally backed by ``path``."""

        super().__init__(path, table="import_upload_cache")

    def set(self, token: str, upload: CachedUpload) -> None:
        """Store ``upload`` metadata for ``token``."""

        payload = json.dumps({"path": str(upload.path), "fmt": upload.fmt})
        super().set(token, payload, upload.expires_at)

    def get(self, token: str) -> CachedUpload | None:
        """Return cached upload for ``token`` if it exists."""

        record = super().get(token)
        if record is None:
            return None
        value, expires_at = record
        data = json.loads(value)
        return CachedUpload(path=Path(data["path"]), fmt=str(data["fmt"]), expires_at=expires_at)

    def delete(self, token: str) -> CachedUpload | None:
        """Remove cached upload for ``token`` returning it when found."""

        record = super().delete(token)
        if record is None:
            return None
        value, expires_at = record
        data = json.loads(value)
        return CachedUpload(path=Path(data["path"]), fmt=str(data["fmt"]), expires_at=expires_at)

    def purge(self, before: datetime) -> List[Tuple[str, CachedUpload]]:
        """Delete uploads expiring before ``before`` returning removed entries."""

        rows = super().purge(before)
        result: List[Tuple[str, CachedUpload]] = []
        for token, value, expires_at in rows:
            data = json.loads(value)
            result.append(
                (
                    token,
                    CachedUpload(
                        path=Path(data["path"]), fmt=str(data["fmt"]), expires_at=expires_at
                    ),
                )
            )
        return result

    def items(self) -> Iterable[Tuple[str, CachedUpload]]:
        """Yield cached uploads that are currently stored."""

        for token, value, expires_at in super().items():
            data = json.loads(value)
            yield (
                token,
                CachedUpload(path=Path(data["path"]), fmt=str(data["fmt"]), expires_at=expires_at),
            )


# The End

