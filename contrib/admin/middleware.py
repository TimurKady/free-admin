# -*- coding: utf-8 -*-
"""
Admin app-level middleware.

Version: 0.0.1
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

from config.settings import settings
from contrib.admin.models.users import AdminUser as AdminUserORM

from .core.settings import SettingsKey, system_config


class AdminGuardMiddleware(BaseHTTPMiddleware):
    """Global guard for the admin interface.

    Performs 307 redirects to /<prefix>/setup if no superuser exists
    and to /<prefix>/login if there is no valid session.
    """

    def __init__(self, app):
        super().__init__(app)
        self.prefix = settings.ADMIN_PATH.rstrip("/")

    async def dispatch(self, request, call_next: Callable[..., Awaitable]):
        path = request.url.path
        if not path.startswith(self.prefix):
            return await call_next(request)

        rel = path[len(self.prefix):] or "/"
        login_path = await system_config.get(SettingsKey.LOGIN_PATH)
        logout_path = await system_config.get(SettingsKey.LOGOUT_PATH)
        setup_path = await system_config.get(SettingsKey.SETUP_PATH)
        static_path = await system_config.get(SettingsKey.STATIC_PATH)
        if (
            rel.startswith(login_path)
            or rel.startswith(logout_path)
            or rel.startswith(setup_path)
            or rel.startswith(static_path)
        ):
            return await call_next(request)

        if not await AdminUserORM.filter(is_staff=True, is_superuser=True).exists():
            return RedirectResponse(f"{self.prefix}{setup_path}", status_code=307)

        session_key = await system_config.get(SettingsKey.SESSION_KEY)
        user_id = request.session.get(session_key)
        if not user_id:
            return RedirectResponse(f"{self.prefix}{login_path}", status_code=307)

        user = await AdminUserORM.get_or_none(id=user_id)
        if not user or not user.is_active or not user.is_staff:
            return RedirectResponse(f"{self.prefix}{login_path}", status_code=307)

        request.state.user = user
        return await call_next(request)

# The End
