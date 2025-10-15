# -*- coding: utf-8 -*-
"""
auth

Authentication utilities for the admin site.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

from .services.auth import AdminAuthService, AuthService
from freeadmin.core.boot import admin as boot_admin

auth_service = AuthService(boot_admin.adapter)
admin_auth_service = AdminAuthService(auth_service, boot_admin.adapter)


def build_auth_router(templates: Jinja2Templates) -> APIRouter:
    """Create and return the admin authentication router."""
    return admin_auth_service.build_auth_router(templates)


# The End

