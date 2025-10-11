# -*- coding: utf-8 -*-
"""
hub

Admin hub configuration and autodiscovery helpers.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import logging
from typing import Iterable, List, Optional

from fastapi import FastAPI

from .conf import (
    FreeAdminSettings,
    current_settings,
    register_settings_observer,
)
from .core.site import AdminSite
from .core.discovery import DiscoveryService
from .router import AdminRouter
from .boot import admin as boot_admin


class AdminHub:
    """Encapsulates admin site configuration and setup."""

    logger = logging.getLogger(__name__)

    def __init__(
        self,
        title: str | None = None,
        *,
        settings: FreeAdminSettings | None = None,
    ) -> None:
        """Initialize the admin site and supporting discovery service."""

        self._settings = settings or current_settings()
        site_title = title or self._settings.admin_site_title
        self.admin_site = AdminSite(
            boot_admin.adapter, title=site_title, settings=self._settings
        )
        self.discovery = DiscoveryService()
        register_settings_observer(self._handle_settings_update)

    def autodiscover(self, packages: Iterable[str]) -> None:
        """Discover admin modules, views, and services within ``packages``."""

        roots = list(packages)
        if not roots:
            return
        self.discovery.discover_all(roots)

    def init_app(self, app: FastAPI, *, packages: Optional[List[str]] = None) -> None:
        """Convenience shortcut: autodiscover followed by mounting the admin."""
        if packages:
            self.autodiscover(packages)
        AdminRouter(self.admin_site).mount(app)

    def _handle_settings_update(self, settings: FreeAdminSettings) -> None:
        """Propagate new configuration to managed services."""
        self._settings = settings
        self.admin_site._settings = settings
        if hasattr(self.admin_site.cards, "apply_settings"):
            self.admin_site.cards.apply_settings(settings)
        else:  # pragma: no cover - compatibility branch
            self.admin_site.cards._settings = settings
            self.admin_site.cards.configure_event_cache(path=settings.event_cache_path)


hub = AdminHub()
admin_site = hub.admin_site

# The End

