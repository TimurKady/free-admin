# -*- coding: utf-8 -*-
"""
__init__

Compatibility facade exposing ORM helpers from the data package.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from ..data.orm import ORMConfig, ORMLifecycle

__all__ = ["ORMConfig", "ORMLifecycle"]


# The End

