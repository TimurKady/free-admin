# -*- coding: utf-8 -*-
"""
conf

Compatibility facade exposing configuration helpers from the configuration package.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from .configuration.conf import FreeAdminSettings, current_settings, register_settings_observer

__all__ = ["FreeAdminSettings", "current_settings", "register_settings_observer"]


# The End

