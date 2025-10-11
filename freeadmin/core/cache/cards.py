# -*- coding: utf-8 -*-
"""cards

SQLite-backed cache storing serialized dashboard card payloads.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Tuple

from .sqlite_kv import SQLiteKeyValueCache


class SQLiteCardCache(SQLiteKeyValueCache):
    """Persist serialized card payloads keyed by user identifier."""

    def __init__(
        self,
        path: str | None = None,
        *,
        table_name: str = "card_cache",
        ttl: timedelta | None = None,
    ) -> None:
        """Initialize the cache with optional SQLite ``path`` and ``ttl``."""

        super().__init__(path=path, table_name=table_name)
        self._ttl = ttl or timedelta(minutes=5)

    def store(self, user_key: str, entries: List[Dict[str, Any]], snapshot: str) -> None:
        """Persist ``entries`` for ``user_key`` tagged with ``snapshot`` token."""

        created_at = datetime.now(timezone.utc)
        payload = {
            "snapshot": snapshot,
            "created_at": created_at.isoformat(),
            "entries": entries,
        }
        expires_at = created_at + self._ttl
        super().set(user_key, json.dumps(payload).encode("utf-8"), expires_at)

    def load(self, user_key: str) -> Tuple[List[Dict[str, Any]], datetime, str] | None:
        """Return cached card entries for ``user_key`` when available."""

        result = super().get(user_key)
        if result is None:
            return None
        payload, _expires_at = result
        data = json.loads(payload.decode("utf-8"))
        created_at = datetime.fromisoformat(str(data.get("created_at")))
        snapshot = str(data.get("snapshot", ""))
        entries = [dict(item) for item in data.get("entries", [])]
        return entries, created_at, snapshot

    def invalidate_user(self, user_key: str) -> None:
        """Remove cached payload belonging to ``user_key`` if present."""

        super().delete(user_key)

    def clear(self) -> None:
        """Remove all cached card payloads."""

        with self._lock:
            assert self._connection is not None
            self._connection.execute(f"DELETE FROM {self._table}")
            self._connection.commit()


__all__: Iterable[str] = ["SQLiteCardCache"]


# The End

