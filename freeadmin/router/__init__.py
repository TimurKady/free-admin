# -*- coding: utf-8 -*-
"""
router

Backward-compatible re-export of router helpers.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from ..core.network.router import (
    AdminRouter,
    ExtendedRouterAggregator,
    RouterAggregator,
)

__all__ = ["AdminRouter", "ExtendedRouterAggregator", "RouterAggregator"]


# The End
