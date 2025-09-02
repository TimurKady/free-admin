# -*- coding: utf-8 -*-
"""
hub

Admin hub configuration and autodiscovery helpers.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
import importlib
import pkgutil
from typing import Iterable, List, Optional

from fastapi import FastAPI

from .core.site import AdminSite
from .router import AdminRouter
from config.settings import settings
from .boot import admin as boot_admin


class AdminHub:
    """Encapsulates admin site configuration and setup."""

    def __init__(self, title: str) -> None:
        self.admin_site = AdminSite(boot_admin.adapter, title=title)

    def autodiscover(self, packages: Iterable[str]) -> None:
        """Import all *.admin and *.admin.* modules within the given packages."""
        for pkg in packages:
            try:
                root = importlib.import_module(pkg)
            except Exception:
                continue
            if not hasattr(root, "__path__"):
                continue
            prefix = root.__name__ + "."
            for finder, modname, ispkg in pkgutil.walk_packages(root.__path__, prefix):
                if modname.endswith(".admin") or ".admin." in modname:
                    importlib.import_module(modname)

    def init_app(self, app: FastAPI, *, packages: Optional[List[str]] = None) -> None:
        """Convenience shortcut: autodiscover followed by mounting the admin."""
        if packages:
            self.autodiscover(packages)
        AdminRouter(self.admin_site).mount(app)


hub = AdminHub(title=settings.ADMIN_SITE_TITLE)
admin_site = hub.admin_site

# The End

