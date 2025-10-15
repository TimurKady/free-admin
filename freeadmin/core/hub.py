# -*- coding: utf-8 -*-
"""
hub

Compatibility bridge exposing the admin hub from the runtime package.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from .runtime.hub import AdminHub, admin_site, hub

__all__ = ["AdminHub", "admin_site", "hub"]


# The End

