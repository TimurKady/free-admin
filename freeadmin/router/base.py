# -*- coding: utf-8 -*-
"""
router

Admin router utilities for mounting the admin site.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from pathlib import Path

from typing import TYPE_CHECKING

from fastapi import FastAPI

from ..conf import FreeAdminSettings, current_settings
from ..core.site import AdminSite
from ..provider import TemplateProvider

if TYPE_CHECKING:  # pragma: no cover - convenience for type checkers
    from .aggregator import RouterAggregator

ASSETS_DIR = Path(__file__).resolve().parent.parent / "static"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class RouterFoundation:
    """Provide shared helpers for router managers."""

    def __init__(self, *, settings: FreeAdminSettings | None = None) -> None:
        """Initialise configuration and the template provider."""

        self._settings = settings or current_settings()
        self._provider = TemplateProvider(
            templates_dir=str(TEMPLATES_DIR),
            static_dir=str(ASSETS_DIR),
            settings=self._settings,
        )

    @property
    def provider(self) -> TemplateProvider:
        """Return the template provider used for admin integration."""

        return self._provider

    def ensure_site_templates(self, site: AdminSite) -> None:
        """Attach template environment to ``site`` when missing."""

        if site.templates is None:
            site.templates = self._provider.get_templates()

    def mount_static_resources(self, app: FastAPI, prefix: str) -> None:
        """Expose admin static files, favicon, and media on ``app``."""

        self._provider.mount_static(app, prefix)
        self._provider.mount_favicon(app)
        self._provider.mount_media(app)


class AdminRouter:
    """Encapsulates mounting the admin interface onto an application."""

    def __init__(
        self,
        site: AdminSite,
        prefix: str | None = None,
        *,
        settings: FreeAdminSettings | None = None,
    ) -> None:
        """Create an aggregator-backed admin router."""

        from .aggregator import RouterAggregator

        self._aggregator = RouterAggregator(
            site=site,
            prefix=prefix,
            settings=settings,
        )

    def mount(self, app: FastAPI) -> None:
        """Mount the admin interface onto the given application."""

        self._aggregator.mount(app)

    @property
    def aggregator(self) -> "RouterAggregator":
        """Return the router aggregator powering this wrapper."""

        return self._aggregator

# The End

