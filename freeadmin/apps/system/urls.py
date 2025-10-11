# -*- coding: utf-8 -*-
"""
urls

URL registration helpers for the system application.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from ...core.site import AdminSite
from .views import BuiltinPagesRegistrar, BuiltinUserMenuRegistrar


class SystemURLRegistrar:
    """Coordinate registration of system routes and menus."""

    def __init__(self) -> None:
        """Instantiate registrars used by the system application."""

        self._page_registrar = BuiltinPagesRegistrar()
        self._user_menu_registrar = BuiltinUserMenuRegistrar()

    def register(self, site: AdminSite) -> None:
        """Register all system routes with ``site``."""

        self._page_registrar.register(site)
        self._user_menu_registrar.register(site)


# The End
