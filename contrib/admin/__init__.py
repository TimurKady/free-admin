# -*- coding: utf-8 -*-
"""
__init__

Admin module entry point.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from importlib import import_module


def __getattr__(name: str):  # pragma: no cover - simple proxy
    if name == "AdminSite":
        return import_module("contrib.admin.core.site").AdminSite
    if name == "BaseModelAdmin":
        return import_module("contrib.admin.core.base").BaseModelAdmin
    if name == "AdminRouter":
        return import_module("contrib.admin.router").AdminRouter
    raise AttributeError(name)


__all__ = ["AdminSite", "BaseModelAdmin", "AdminRouter"]

__version__ = "0.1.0-dev"

# The End

