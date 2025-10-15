# -*- coding: utf-8 -*-
"""urls

Routing configuration for the admin system API views.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from fastapi import APIRouter

from .views import AdminAPIViewSet, AdminAPIConfiguration

_config = AdminAPIConfiguration()
_viewset = AdminAPIViewSet(_config)
router = APIRouter()
_viewset.register(router)
API_PREFIX = _config.api_prefix

__all__ = ["API_PREFIX", "router"]

# The End

