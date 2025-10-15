# -*- coding: utf-8 -*-
"""menu

SQLite-backed cache for serialized main menu payloads.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Tuple, TYPE_CHECKING

from .sqlite_kv import SQLiteKeyValueCache

if TYPE_CHECKING:  # pragma: no cover
    from ..registry import MenuItem


class MainMenuCache(SQLiteKeyValueCache):
    """Persist main menu payloads keyed by registry version and locale."""

    def __init__(
        self,
        path: str | None = None,
        *,
        table_name: str = "main_menu_cache",
        ttl: timedelta | None = None,
    ) -> None:
        """Initialize the cache with an optional persistence ``path``."""

        super().__init__(path=path, table_name=table_name)
        self._ttl = ttl or timedelta(minutes=30)

    def store(
        self,
        version: int,
        locale: str | None,
        items: List["MenuItem"],
        *,
        config_token: str | None = None,
    ) -> None:
        """Serialize and persist ``items`` for ``version`` and ``locale``."""

        key = self._compose_key(version, locale, config_token)
        created_at = datetime.now(timezone.utc)
        payload = {
            "version": version,
            "locale": locale or "",
            "created_at": created_at.isoformat(),
            "items": [asdict(item) for item in items],
        }
        if config_token:
            payload["settings_fingerprint"] = config_token
        expires_at = created_at + self._ttl
        super().set(key, json.dumps(payload).encode("utf-8"), expires_at)

    def load(
        self,
        version: int,
        locale: str | None,
        *,
        config_token: str | None = None,
    ) -> Tuple[List["MenuItem"], datetime] | None:
        """Return cached menu items and timestamp for the key if present."""

        key = self._compose_key(version, locale, config_token)
        result = super().get(key)
        if result is None:
            return None
        payload, _expires_at = result
        data = json.loads(payload.decode("utf-8"))
        created_at = datetime.fromisoformat(str(data["created_at"]))
        items = [
            self._deserialize_item(raw)
            for raw in data.get("items", [])
        ]
        return items, created_at

    def clear(self) -> None:
        """Remove all cached menu payloads."""

        with self._lock:
            assert self._connection is not None
            self._connection.execute(f"DELETE FROM {self._table}")
            self._connection.commit()

    def _compose_key(
        self,
        version: int,
        locale: str | None,
        config_token: str | None = None,
    ) -> str:
        return f"{version}:{(locale or '').strip()}:{config_token or ''}"

    def _deserialize_item(self, data: dict) -> "MenuItem":
        from ..registry import MenuItem  # local import to avoid cycle

        return MenuItem(
            title=str(data.get("title", "")),
            path=str(data.get("path", "")),
            icon=data.get("icon"),
            page_type=data.get("page_type"),
        )


__all__: Iterable[str] = ["MainMenuCache"]


# The End

