# -*- coding: utf-8 -*-
"""
apps

Example application package collection.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from .base import ExampleAppConfig
from .demo.app import DemoConfig

__all__ = ["DemoConfig", "ExampleAppConfig"]

# The End

