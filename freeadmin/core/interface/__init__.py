# -*- coding: utf-8 -*-
"""
interface

Admin interface building blocks for FreeAdmin.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from .app import AppConfig
from .discovery import DiscoveryService
from .filters import FilterSpec
from .site import AdminSite

__all__ = [
    "AppConfig",
    "DiscoveryService",
    "FilterSpec",
    "AdminSite",
]


# The End
