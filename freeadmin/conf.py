# -*- coding: utf-8 -*-
"""
conf

Backward-compatible re-export of configuration helpers.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from .core.configuration.conf import (
    FreeAdminSettings,
    SettingsManager,
    configure,
    current_settings,
    register_settings_observer,
    unregister_settings_observer,
)

__all__ = [
    "FreeAdminSettings",
    "SettingsManager",
    "configure",
    "current_settings",
    "register_settings_observer",
    "unregister_settings_observer",
]


# The End
