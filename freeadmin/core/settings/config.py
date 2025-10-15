# -*- coding: utf-8 -*-
"""
config

Compatibility bridge exposing settings configuration helpers from the interface layer.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from importlib import import_module

_settings_module = import_module("freeadmin.core.interface.settings.config")

SystemConfig = _settings_module.SystemConfig
system_config = _settings_module.system_config
DATABASE_OPERATION_ERRORS = _settings_module.DATABASE_OPERATION_ERRORS
logger = _settings_module.logger

__all__ = ["SystemConfig", "system_config", "DATABASE_OPERATION_ERRORS", "logger"]


# The End

