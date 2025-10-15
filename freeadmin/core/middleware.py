# -*- coding: utf-8 -*-
"""
middleware

Compatibility bridge exposing runtime middleware from the core package.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from .runtime.middleware import AdminGuardMiddleware

__all__ = ["AdminGuardMiddleware"]


# The End

