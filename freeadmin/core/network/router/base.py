# -*- coding: utf-8 -*-
"""
router

Admin router utilities for mounting the admin site.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from fastapi import FastAPI

from ...conf import FreeAdminSettings, current_settings
from ...interface.site import AdminSite
from ...interface.templates import TemplateService

if TYPE_CHECKING:  # pragma: no cover - convenience for type checkers
    from .aggregator import RouterAggregator
    from ..runtime.provider import TemplateProvider


class RouterFoundation:
    """Provide shared helpers for router managers."""

    def __init__(
        self,
        *,
        settings: FreeAdminSettings | None = None,
        template_service: TemplateService | None = None,
    ) -> None:
        """Initialise configuration and template integration helpers."""

        self._settings = settings or current_settings()
        self._template_service = template_service or TemplateService(
            settings=self._settings
        )

    @property
    def template_service(self) -> TemplateService:
        """Return the template service used for admin integration."""

        return self._template_service

    @property
    def provider(self) -> "TemplateProvider":
        """Return the template provider configured for admin integration."""

        return self._template_service.get_provider()

    def ensure_site_templates(self, site: AdminSite) -> None:
        """Attach template environment to ``site`` when missing."""

        self._template_service.ensure_site_templates(site)

    def mount_static_resources(self, app: FastAPI, prefix: str) -> None:
        """Expose admin static files, favicon, and media on ``app``."""

        self._template_service.mount_static_resources(app, prefix)


class AdminRouter:
    """Encapsulates mounting the admin interface onto an application."""

    def __init__(
        self,
        site: AdminSite,
        prefix: str | None = None,
        *,
        settings: FreeAdminSettings | None = None,
        template_service: TemplateService | None = None,
    ) -> None:
        """Create an aggregator-backed admin router."""

        from .aggregator import RouterAggregator

        self._aggregator = RouterAggregator(
            site=site,
            prefix=prefix,
            settings=settings,
            template_service=template_service,
        )

    def mount(self, app: FastAPI) -> None:
        """Mount the admin interface onto the given application."""

        self._aggregator.mount(app)

    @property
    def aggregator(self) -> "RouterAggregator":
        """Return the router aggregator powering this wrapper."""

        return self._aggregator

# The End

