# -*- coding: utf-8 -*-
"""
menu

Admin menu builder utilities decoupled from the page registry.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Dict, List, Tuple, TYPE_CHECKING

from .registry import MenuItem, UserMenuItem
from .settings import SettingsKey, system_config
from .cache.menu import MainMenuCache

if TYPE_CHECKING:  # pragma: no cover
    from .registry import PageRegistry


class MenuBuilder:
    """Manage menu entries and assemble rendered menu structures."""

    def __init__(
        self,
        registry: "PageRegistry",
        *,
        cache: MainMenuCache | None = None,
    ) -> None:
        """Initialize collections and bind the builder to ``registry``."""

        self._registry = registry
        self._items: List[MenuItem] = []
        self._user_items: List[UserMenuItem] = []
        self._cache = cache or MainMenuCache()

    def register_item(
        self,
        title: str,
        path: str,
        icon: str | None = None,
        page_type: str | None = None,
    ) -> None:
        """Register a main navigation menu item."""

        self._items.append(MenuItem(title=title, path=path, icon=icon, page_type=page_type))
        self._registry.bump_version()

    def register_user_item(
        self,
        title: str,
        path: str,
        icon: str | None = None,
    ) -> None:
        """Register a user menu entry avoiding duplicates by path."""

        for item in self._user_items:
            if item.path == path:
                return
        self._user_items.append(UserMenuItem(title=title, path=path, icon=icon))
        self._registry.bump_version()

    def build_main_menu(
        self,
        registry: "PageRegistry" | None = None,
        *,
        locale: str | None = None,
    ) -> List[MenuItem]:
        """Return the assembled main menu using cached payloads when available."""

        target_registry = registry or self._registry
        locale_token = self._resolve_locale(locale)
        settings_bundle = self._resolve_menu_settings()
        config_token = self._compose_settings_token(settings_bundle)
        cached = self._cache.load(
            target_registry.registry_version,
            locale_token,
            config_token=config_token,
        )
        if cached is not None:
            items, _created_at = cached
            return list(items)

        default_page_type = settings_bundle["default_page_type"]
        menu: List[MenuItem] = [
            MenuItem(
                title=item.title,
                path=item.path,
                icon=item.icon,
                page_type=item.page_type or default_page_type,
            )
            for item in self._items
        ]
        orm_prefix = settings_bundle["orm_prefix"]
        settings_prefix = settings_bundle["settings_prefix"]
        orm_page_type = settings_bundle["orm_page_type"]
        settings_page_type = settings_bundle["settings_page_type"]
        for entry in target_registry.iter_orm():
            menu.append(
                MenuItem(
                    title=entry.name or entry.model,
                    path=f"{orm_prefix}/{entry.app}/{entry.model}",
                    icon=entry.icon,
                    page_type=orm_page_type,
                )
            )
        for entry in target_registry.iter_settings():
            menu.append(
                MenuItem(
                    title=entry.name or entry.model,
                    path=f"{settings_prefix}/{entry.app}/{entry.model}",
                    icon=entry.icon,
                    page_type=settings_page_type,
                )
            )
        self._cache.store(
            target_registry.registry_version,
            locale_token,
            menu,
            config_token=config_token,
        )
        return menu

    def build_user_menu(self, registry: "PageRegistry") -> List[UserMenuItem]:
        """Return registered user menu entries."""

        _ = registry
        return list(self._user_items)

    def invalidate_main_menu(self) -> None:
        """Remove all cached main menu payloads."""

        self._cache.clear()

    def _resolve_locale(self, locale: str | None) -> str:
        """Return a normalized locale token for cache lookups."""

        candidate = (locale or "").strip()
        if candidate:
            return candidate
        return str(system_config.get_cached(SettingsKey.DEFAULT_LOCALE, "en"))

    def _resolve_menu_settings(self) -> dict[str, str]:
        """Return the configuration values that influence the main menu."""

        return {
            "default_page_type": str(
                system_config.get_cached(SettingsKey.PAGE_TYPE_VIEW, "view")
            ),
            "orm_prefix": str(system_config.get_cached(SettingsKey.ORM_PREFIX, "/orm")),
            "settings_prefix": str(
                system_config.get_cached(SettingsKey.SETTINGS_PREFIX, "/settings")
            ),
            "orm_page_type": str(
                system_config.get_cached(SettingsKey.PAGE_TYPE_ORM, "orm")
            ),
            "settings_page_type": str(
                system_config.get_cached(SettingsKey.PAGE_TYPE_SETTINGS, "settings")
            ),
        }

    @staticmethod
    def _compose_settings_token(settings_bundle: dict[str, str]) -> str:
        """Return a stable fingerprint for ``settings_bundle`` contents."""

        return "|".join(
            f"{key}={settings_bundle[key]}" for key in sorted(settings_bundle)
        )


class PublicMenuCache:
    """Maintain cached snapshots of the public menu."""

    def __init__(self) -> None:
        """Initialise the in-memory storage for cached payloads."""

        self._payloads: Dict[Tuple[int, str], List[MenuItem]] = {}

    def load(self, version: int, prefix: str) -> List[MenuItem] | None:
        """Return cached menu items for the ``version`` and ``prefix`` pair."""

        cached = self._payloads.get((version, prefix))
        if cached is None:
            return None
        return list(cached)

    def store(self, version: int, prefix: str, items: List[MenuItem]) -> None:
        """Persist ``items`` for the cache key identified by ``version``."""

        self._payloads[(version, prefix)] = list(items)

    def clear(self) -> None:
        """Remove all cached menu payloads."""

        self._payloads.clear()


class PublicMenuBuilder:
    """Manage public navigation items exposed outside the admin interface."""

    def __init__(
        self,
        *,
        cache: PublicMenuCache | None = None,
    ) -> None:
        """Initialise storage for registered items and optional cache."""

        self._items: Dict[str, MenuItem] = {}
        self._order: List[str] = []
        self._version: int = 0
        self._cache = cache or PublicMenuCache()

    def register_item(
        self,
        *,
        title: str,
        path: str,
        icon: str | None = None,
    ) -> None:
        """Register or update a public navigation entry."""

        normalized_path = self._normalize_path(path)
        item = MenuItem(title=title, path=normalized_path, icon=icon)
        existing = self._items.get(normalized_path)
        if existing == item:
            return
        if normalized_path not in self._items:
            self._order.append(normalized_path)
        self._items[normalized_path] = item
        self._version += 1
        self._cache.clear()

    def build_menu(self, *, prefix: str | None = None) -> List[MenuItem]:
        """Return public menu items adjusted for the configured ``prefix``."""

        normalized_prefix = self._normalize_prefix(prefix)
        cached = self._cache.load(self._version, normalized_prefix)
        if cached is not None:
            return list(cached)

        items: List[MenuItem] = []
        for key in self._order:
            item = self._items.get(key)
            if item is None:
                continue
            resolved_path = self._compose_path(normalized_prefix, item.path)
            items.append(
                MenuItem(
                    title=item.title,
                    path=resolved_path,
                    icon=item.icon,
                    page_type=item.page_type,
                )
            )

        self._cache.store(self._version, normalized_prefix, items)
        return list(items)

    def clear(self) -> None:
        """Remove registered items and cached payloads."""

        self._items.clear()
        self._order.clear()
        self._version += 1
        self._cache.clear()

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Return a normalised absolute path for ``path``."""

        candidate = (path or "/").strip()
        if not candidate:
            candidate = "/"
        if not candidate.startswith("/"):
            candidate = f"/{candidate}"
        if len(candidate) > 1 and candidate.endswith("/"):
            candidate = candidate.rstrip("/")
        return candidate or "/"

    @staticmethod
    def _normalize_prefix(prefix: str | None) -> str:
        """Return a canonical representation for ``prefix``."""

        if prefix is None:
            return ""
        candidate = prefix.strip()
        if not candidate or candidate == "/":
            return ""
        if not candidate.startswith("/"):
            candidate = f"/{candidate}"
        return candidate.rstrip("/")

    @classmethod
    def _compose_path(cls, prefix: str, path: str) -> str:
        """Combine ``prefix`` and ``path`` into a navigable URL."""

        normalized_path = cls._normalize_path(path)
        if not prefix:
            return normalized_path
        tail = normalized_path.lstrip("/")
        if not tail:
            return prefix or "/"
        return f"{prefix}/{tail}"


__all__ = ["MenuBuilder", "PublicMenuBuilder", "PublicMenuCache"]


# The End

