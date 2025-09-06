# -*- coding: utf-8 -*-
"""
router

Admin router utilities for mounting the admin site.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI
from config.settings import settings

from .core.settings import SettingsKey, system_config
from .core.site import AdminSite
from .provider import TemplateProvider

ASSETS_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"


class AdminRouter:
    """Encapsulates mounting the admin interface onto an application."""

    def __init__(
        self,
        site: AdminSite,
        prefix: str = system_config.get_cached(
            SettingsKey.ADMIN_PREFIX, settings.ADMIN_PATH
        ),
    ) -> None:
        # "prefix" may be supplied with a trailing slash; remove it for
        # consistency so paths can be concatenated safely.
        self.site = site
        self.prefix = prefix.rstrip("/")
        self._provider = TemplateProvider(
            templates_dir=str(TEMPLATES_DIR), static_dir=str(ASSETS_DIR)
        )

    def mount(self, app: FastAPI) -> None:
        """Mount the admin interface onto the given application."""
        if self.site.templates is None:
            self.site.templates = self._provider.get_templates()

        app.state.admin_site = self.site
        router = self.site.build_router(self._provider)
        app.include_router(router, prefix=self.prefix)
        self._provider.mount_static(app, self.prefix)
        self._provider.mount_favicon(app)
        self._provider.mount_media(app)

# The End

