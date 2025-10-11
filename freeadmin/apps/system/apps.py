# -*- coding: utf-8 -*-
"""
apps

Application configuration for the built-in system app.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import ClassVar

from ...core.site import AdminSite
from .urls import SystemURLRegistrar


class SystemAppConfig:
    """App configuration mirroring Django's :class:`~django.apps.AppConfig`."""

    name: ClassVar[str] = "freeadmin.apps.system"
    label: ClassVar[str] = "system"
    verbose_name: ClassVar[str] = "System Administration"

    def __init__(self) -> None:
        """Initialize registrars required by the system application."""

        self._urls = SystemURLRegistrar()

    @property
    def urls(self) -> SystemURLRegistrar:
        """Return the URL registrar responsible for wiring system routes."""

        return self._urls

    def ready(self, site: AdminSite) -> None:
        """Register built-in URLs and menus against ``site``."""

        self._urls.register(site)


default_app_config = SystemAppConfig()


# The End
