# -*- coding: utf-8 -*-
"""
config

Configuration helpers for the FreeAdmin example project.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from .orm import ExampleORMConfig
from .main import ExampleApplication
from .routers import ExampleRouterAggregator
from .settings import ExampleSettings

__all__ = [
    "ExampleApplication",
    "ExampleORMConfig",
    "ExampleRouterAggregator",
    "ExampleSettings",
]

# The End

