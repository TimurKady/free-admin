# -*- coding: utf-8 -*-
"""permissions

SQLite-backed cache storing per-user permission outcomes.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from .sqlite_kv import SQLiteKeyValueCache


class SQLitePermissionCache(SQLiteKeyValueCache):
    """Cache boolean permission checks keyed by user, content type and action."""

    def __init__(
        self,
        path: str | None = None,
        *,
        table_name: str = "permission_cache",
        ttl: timedelta | None = None,
    ) -> None:
        """Initialize the permission cache backing store."""

        super().__init__(path=path, table_name=table_name)
        self._ttl = ttl or timedelta(minutes=5)

    def store_permission(
        self,
        user_id: str,
        content_type_id: str,
        action: str,
        allowed: bool,
    ) -> None:
        """Persist ``allowed`` outcome for the specified permission tuple."""

        key = self._compose_key(user_id, content_type_id, action)
        expires_at = datetime.now(timezone.utc) + self._ttl
        payload = b"1" if allowed else b"0"
        super().set(key, payload, expires_at)

    def get_permission(
        self, user_id: str, content_type_id: str, action: str
    ) -> bool | None:
        """Return cached permission outcome for the given tuple when present."""

        key = self._compose_key(user_id, content_type_id, action)
        record = super().get(key)
        if record is None:
            return None
        payload, _expires_at = record
        return payload == b"1"

    def invalidate_user(self, user_id: str) -> int:
        """Remove cached results associated with ``user_id``."""

        prefix = f"{user_id}:"
        with self._lock:
            assert self._connection is not None
            cursor = self._connection.execute(
                f"DELETE FROM {self._table} WHERE key LIKE ?",
                (f"{prefix}%",),
            )
            deleted = cursor.rowcount
            self._connection.commit()
        return int(deleted)

    def invalidate_group(
        self, group_id: str, member_user_ids: Iterable[str] | None = None
    ) -> int:
        """Remove cached results for users that belong to ``group_id``."""

        if not member_user_ids:
            return 0
        removed = 0
        for member in {str(user_id) for user_id in member_user_ids}:
            removed += self.invalidate_user(member)
        return removed

    def _compose_key(self, user_id: str, content_type_id: str, action: str) -> str:
        return f"{user_id}:{content_type_id}:{action}"


__all__ = ["SQLitePermissionCache"]


# The End
