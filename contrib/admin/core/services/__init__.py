# -*- coding: utf-8 -*-
"""
services

Service layer for admin CRUD operations.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from .auth import AdminAuthService
from .tokens import ScopeTokenService
from .permissions import PermAction, PermissionsService, permissions_service
from .scope_query import ScopeQueryService

__all__ = [
    "AdminAuthService",
    "ScopeTokenService",
    "ScopeQueryService",
    "PermAction",
    "PermissionsService",
    "permissions_service",
]

# The End

