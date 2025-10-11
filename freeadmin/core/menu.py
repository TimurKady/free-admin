# -*- coding: utf-8 -*-
"""
menu

Admin menu builder utilities decoupled from the page registry.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import List, TYPE_CHECKING

from .registry import MenuItem, UserMenuItem
from .settings import SettingsKey, system_config

if TYPE_CHECKING:  # pragma: no cover
    from .registry import PageRegistry


class MenuBuilder:
    """Manage menu entries and assemble rendered menu structures."""

    def __init__(self) -> None:
        """Initialize empty collections for menu items."""
        self._items: List[MenuItem] = []
        self._user_items: List[UserMenuItem] = []

    def register_item(
        self,
        title: str,
        path: str,
        icon: str | None = None,
        page_type: str | None = None,
    ) -> None:
        """Register a main navigation menu item."""
        self._items.append(MenuItem(title=title, path=path, icon=icon, page_type=page_type))

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

    def build_main_menu(self, registry: "PageRegistry") -> List[MenuItem]:
        """Return the assembled main menu using registered entries and view pages."""
        default_page_type = system_config.get_cached(SettingsKey.PAGE_TYPE_VIEW, "view")
        menu: List[MenuItem] = [
            MenuItem(
                title=item.title,
                path=item.path,
                icon=item.icon,
                page_type=item.page_type or default_page_type,
            )
            for item in self._items
        ]
        orm_prefix = system_config.get_cached(SettingsKey.ORM_PREFIX, "/orm")
        settings_prefix = system_config.get_cached(SettingsKey.SETTINGS_PREFIX, "/settings")
        orm_page_type = system_config.get_cached(SettingsKey.PAGE_TYPE_ORM, "orm")
        settings_page_type = system_config.get_cached(
            SettingsKey.PAGE_TYPE_SETTINGS, "settings"
        )
        for entry in registry.iter_orm():
            menu.append(
                MenuItem(
                    title=entry.name or entry.model,
                    path=f"{orm_prefix}/{entry.app}/{entry.model}",
                    icon=entry.icon,
                    page_type=orm_page_type,
                )
            )
        for entry in registry.iter_settings():
            menu.append(
                MenuItem(
                    title=entry.name or entry.model,
                    path=f"{settings_prefix}/{entry.app}/{entry.model}",
                    icon=entry.icon,
                    page_type=settings_page_type,
                )
            )
        return menu

    def build_user_menu(self, registry: "PageRegistry") -> List[UserMenuItem]:
        """Return registered user menu entries."""
        _ = registry
        return list(self._user_items)


# The End

