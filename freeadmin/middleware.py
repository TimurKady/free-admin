# -*- coding: utf-8 -*-
"""
middleware

Backward-compatible re-export of admin middleware utilities.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from .core.runtime.middleware import AdminGuardMiddleware

__all__ = ["AdminGuardMiddleware"]


# The End
