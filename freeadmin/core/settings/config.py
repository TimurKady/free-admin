# -*- coding: utf-8 -*-
"""
config

Database-backed system configuration utilities.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import importlib.util
import logging
import sqlite3
from typing import Any, Tuple

from tortoise import exceptions as tortoise_exceptions

from .defaults import DEFAULT_SETTINGS
from .keys import SettingsKey
from ...boot import admin as boot_admin
SystemSetting = boot_admin.adapter.system_setting_model

if importlib.util.find_spec("asyncpg") is not None:
    from asyncpg import exceptions as asyncpg_exceptions

    ASYNCPG_ERRORS: Tuple[type[BaseException], ...] = (
        asyncpg_exceptions.UndefinedTableError,
    ) if hasattr(asyncpg_exceptions, "UndefinedTableError") else ()
else:
    ASYNCPG_ERRORS = ()

TORTOISE_OPERATIONAL_ERRORS: Tuple[type[BaseException], ...] = (
    tortoise_exceptions.OperationalError,
)
if hasattr(tortoise_exceptions, "DBOperationalError"):
    TORTOISE_OPERATIONAL_ERRORS += (tortoise_exceptions.DBOperationalError,)

DATABASE_OPERATION_ERRORS: Tuple[type[BaseException], ...] = (
    sqlite3.OperationalError,
) + TORTOISE_OPERATIONAL_ERRORS + ASYNCPG_ERRORS

logger = logging.getLogger(__name__)


class SystemConfig:
    """Helper for accessing and mutating system settings.

    Values are cached in-memory. ``reload`` repopulates the cache from the
    database and ``ensure_seed`` inserts any missing defaults based on
    :data:`DEFAULT_SETTINGS`.
    """

    def __init__(self) -> None:
        """Initialize an empty in-memory cache for system settings."""

        self._cache: dict[str, Any] = {}

    @property
    def adapter(self) -> Any:
        """Return the active data adapter responsible for persistence."""

        from ...boot import admin as boot_admin

        return boot_admin.adapter

    async def ensure_seed(self) -> None:
        """Ensure all default settings exist in the database.

        Inserts any missing keys from :data:`DEFAULT_SETTINGS` and reloads the
        cache afterwards.
        """

        try:
            await self._seed_defaults()
        except DATABASE_OPERATION_ERRORS as exc:
            logger.warning(
                "Skipping system configuration seed due to database error: %s. "
                "Run your migrations before starting FreeAdmin.",
                exc,
            )

    async def _seed_defaults(self) -> None:
        """Perform the default seeding workflow within a transaction."""

        async with self.adapter.in_transaction():
            # migrate legacy page-type keys if present
            mapping = {
                "orm": SettingsKey.PAGE_TYPE_ORM,
                "view": SettingsKey.PAGE_TYPE_VIEW,
                "settings": SettingsKey.PAGE_TYPE_SETTINGS,
            }
            for bad_key, enum_key in mapping.items():
                record = await self.adapter.get_or_none(SystemSetting, key=bad_key)
                if record is None:
                    continue
                target_key = enum_key.value
                if await self.adapter.exists(
                    self.adapter.filter(SystemSetting, key=target_key)
                ):
                    logger.warning(
                        "SystemSetting key '%s' exists; deleting stray '%s'", target_key, bad_key
                    )
                    await self.adapter.delete(record)
                    continue
                record.key = target_key
                record.name = enum_key.label or target_key
                await self.adapter.save(record)

            for key_enum, (value, value_type) in DEFAULT_SETTINGS.items():
                key = key_enum.value
                existing = await self.adapter.get_or_none(SystemSetting, key=key)
                if existing is None:
                    await self.adapter.create(
                        SystemSetting,
                        key=key,
                        name=getattr(key_enum, "label", key),
                        value=value,
                        value_type=value_type,
                    )
        await self.reload()

    async def reload(self) -> None:
        """Reload settings from the database into the in-memory cache."""

        type_map = {k.value: t for k, (_, t) in DEFAULT_SETTINGS.items()}
        try:
            new_cache: dict[str, Any] = {}
            qs = self.adapter.values(self.adapter.all(SystemSetting), "key", "value")
            for record in await self.adapter.fetch_all(qs):
                key = record["key"]
                value_type = type_map.get(key, "string")
                new_cache[key] = self._cast(record["value"], value_type)

            # Ensure defaults for any keys still missing (in case DB lacked them)
            for key_enum, (value, value_type) in DEFAULT_SETTINGS.items():
                key = key_enum.value
                new_cache.setdefault(key, self._cast(value, value_type))
        except DATABASE_OPERATION_ERRORS as exc:
            logger.warning(
                "Skipping system configuration reload due to database error: %s. "
                "Run your migrations before starting FreeAdmin.",
                exc,
            )
            return

        self._cache.clear()
        self._cache.update(new_cache)

    def get_cached(self, key: SettingsKey | str, default: Any | None = None) -> Any:
        """Return ``key`` value directly from the in-memory cache.

        This helper avoids any disk IO and is safe to use after
        :meth:`reload` has populated the cache. If ``key`` is missing,
        ``default`` is returned instead of raising ``KeyError``.
        """

        key_str = key.value if isinstance(key, SettingsKey) else key
        return self._cache.get(key_str, default)

    async def get(self, key: SettingsKey | str, default: Any | None = None) -> Any:
        """Return a setting value by ``key``.

        ``key`` may be either a :class:`SettingsKey` instance or a raw string.
        If the key is missing and ``default`` is provided, ``default`` is
        returned. Otherwise a :class:`KeyError`` is raised.
        """

        key_str = key.value if isinstance(key, SettingsKey) else key
        if key_str in self._cache:
            return self._cache[key_str]
        if default is not None:
            return default
        raise KeyError(key_str)

    async def set(self, key: SettingsKey | str, value: Any) -> None:
        """Persist ``value`` for ``key`` and update the cache.

        Type casting is performed based on :data:`DEFAULT_SETTINGS` if the key
        is known; otherwise a simple string/integer/bool inference is applied.
        """

        key_str = key.value if isinstance(key, SettingsKey) else key
        value_type = self._resolve_type(key_str, value)
        casted = self._cast(value, value_type)

        existing = await self.adapter.get_or_none(SystemSetting, key=key_str)
        if existing is None:
            await self.adapter.create(
                SystemSetting,
                key=key_str,
                name=(
                    getattr(key, "label", key_str)
                    if isinstance(key, SettingsKey)
                    else key_str
                ),
                value=casted,
                value_type=value_type,
            )
        else:
            existing.value = casted
            existing.value_type = value_type
            await self.adapter.save(existing)

        self._cache[key_str] = casted

    def exists(self, key: SettingsKey | str) -> bool:
        """Return ``True`` if ``key`` is present in the cache."""

        key_str = key.value if isinstance(key, SettingsKey) else key
        return key_str in self._cache

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _cast(value: Any, value_type: str) -> Any:
        if value_type == "int":
            return int(value)
        if value_type == "bool":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in {"1", "true", "yes", "on"}
            return bool(value)
        # default string
        if isinstance(value, str):
            return value
        return str(value)

    def _resolve_type(self, key: str, value: Any) -> str:
        for k, (_, t) in DEFAULT_SETTINGS.items():
            if k.value == key:
                return t
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        return "string"


# Module-level singleton ------------------------------------------------------

system_config = SystemConfig()


# The End

__all__ = ["SystemConfig", "system_config"]

# The End

