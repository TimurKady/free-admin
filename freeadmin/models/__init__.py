# -*- coding: utf-8 -*-
"""
__init__

Single point of connection of Admin Models.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from typing import List

from ..boot import admin as boot_admin
from .autodiscoverer import ModelAutoDiscoverer
from .choices import IntChoices, IntegerChoices, StrChoices, TextChoices  # noqa: F401

try:
    adapter = boot_admin.adapter
    ModelBase = adapter.Model
    PermAction = adapter.perm_action
    SettingValueType = adapter.setting_value_type
    _discoverer = ModelAutoDiscoverer(ModelBase)
    __models__: List[type[ModelBase]] = _discoverer.models
    __all__ = [
        "StrChoices",
        "IntChoices",
        "TextChoices",
        "IntegerChoices",
        "PermAction",
        "SettingValueType",
    ]
except ModuleNotFoundError:  # pragma: no cover - during adapter bootstrap
    adapter = None  # type: ignore
    ModelBase = object  # type: ignore
    PermAction = None  # type: ignore
    SettingValueType = None  # type: ignore
    __models__: List[type[ModelBase]] = []
    __all__ = ["StrChoices", "IntChoices", "TextChoices", "IntegerChoices"]

# The End

