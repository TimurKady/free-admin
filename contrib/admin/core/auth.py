# -*- coding: utf-8 -*-
"""
auth

Authentication utilities for the admin site.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable, TYPE_CHECKING
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from urllib.parse import urlparse

from .auth_service import AuthService
from ..adapters import BaseAdapter
from config.settings import settings
from .settings import SettingsKey, system_config

if TYPE_CHECKING:  # pragma: no cover
    from .site import AdminSite

@dataclass
class AdminUserDTO:
    id: str
    username: str
    email: str = ""
    is_staff: bool = False
    is_superuser: bool = False
    is_active: bool = True
    permissions: set[str] = field(default_factory=set)


class AdminAuthService:
    """Authentication helpers for the admin site."""

    def __init__(self, auth_service: AuthService, adapter: BaseAdapter) -> None:
        self.auth_service = auth_service
        self.adapter = adapter
        self.AdminUserPermission = adapter.user_permission_model
        self.AdminGroupPermission = adapter.group_permission_model
        self.PermAction = adapter.perm_action

    @staticmethod
    def _resolve_icon_path(icon_path: str, prefix: str, static_segment: str) -> str:
        parsed = urlparse(icon_path)
        if parsed.scheme or icon_path.startswith("/"):
            return icon_path
        static_pos = icon_path.find("static/")
        if static_pos != -1:
            icon_path = icon_path[static_pos + len("static/") :]
        return (
            f"{prefix.rstrip('/')}{static_segment.rstrip('/')}/"
            f"{icon_path.lstrip('/')}"
        )

    @property
    def site_title(self) -> str:
        """Return the admin site title."""
        return system_config.get_cached(
            SettingsKey.DEFAULT_ADMIN_TITLE, settings.ADMIN_SITE_TITLE
        )

    @property
    def brand_icon(self) -> str:
        """Return URL to the brand icon."""
        icon_path = system_config.get_cached(
            SettingsKey.BRAND_ICON, settings.BRAND_ICON
        )
        prefix = system_config.get_cached(
            SettingsKey.ADMIN_PREFIX, settings.ADMIN_PATH
        )
        static_segment = system_config.get_cached(
            SettingsKey.STATIC_URL_SEGMENT, "/static"
        )
        return self._resolve_icon_path(icon_path, prefix, static_segment)

    async def get_current_admin_user(self, request: Request) -> AdminUserDTO:
        user = getattr(request.state, "user", None)
        if not user or not getattr(user, "is_active", False):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        perms: set[str] = set()
        if user.is_staff and not user.is_superuser:
            user_perm_qs = self.adapter.filter(
                self.AdminUserPermission, user_id=user.id
            )
            user_perm_qs = self.adapter.prefetch_related(
                user_perm_qs, "content_type"
            )
            user_perms = await self.adapter.fetch_values(
                user_perm_qs, "content_type__dotted", "action"
            )
            for dotted, action in user_perms:
                if dotted:
                    perms.add(f"{str(dotted).lower()}.{str(action)}")
                else:
                    perms.add(str(action))
            group_ids = await self.adapter.fetch_values(
                self.adapter.filter(user.groups), "id", flat=True
            )
            if group_ids:
                group_perm_qs = self.adapter.filter(
                    self.AdminGroupPermission, group_id__in=group_ids
                )
                group_perm_qs = self.adapter.prefetch_related(
                    group_perm_qs, "content_type"
                )
                group_perms = await self.adapter.fetch_values(
                    group_perm_qs, "content_type__dotted", "action"
                )
                for dotted, action in group_perms:
                    if dotted:
                        perms.add(f"{str(dotted).lower()}.{str(action)}")
                    else:
                        perms.add(str(action))
        return AdminUserDTO(
            id=str(user.id),
            username=user.username,
            email=getattr(user, "email", "") or "",
            is_staff=bool(getattr(user, "is_staff", False)),
            is_superuser=bool(getattr(user, "is_superuser", False)),
            is_active=True,
            permissions=perms,
        )

    def require_permissions(
        self, codenames: Iterable[str] = (), *, admin_site: "AdminSite" | None = None
    ):
        """Dependency generator enforcing permission codenames."""

        parsed: list[tuple[str, str, "PermAction"]] = []
        for codename in codenames:
            try:
                app, model, action = codename.split(".")
                parsed.append((app, model, self.PermAction(action)))
            except ValueError:
                raise ValueError(f"Invalid codename: {codename}") from None

        async def _dep(
            request: Request, user: AdminUserDTO = Depends(self.get_current_admin_user)
        ) -> AdminUserDTO:
            if not parsed:
                return user

            site = admin_site or getattr(request.app.state, "admin_site", None)
            if site is None:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

            orm_user = request.state.user
            for app, model, action in parsed:
                ct_id = site.get_ct_id(app, model)
                if ct_id is None:
                    raise HTTPException(status_code=404)
                allowed = False
                if orm_user.is_active and orm_user.is_staff:
                    if orm_user.is_superuser:
                        allowed = True
                    else:
                        allowed = await self.adapter.exists(
                            self.adapter.filter(
                                self.AdminUserPermission,
                                user_id=orm_user.id,
                                content_type_id=ct_id,
                                action=action,
                            )
                        )
                        if not allowed:
                            group_ids = await self.adapter.fetch_values(
                                self.adapter.filter(orm_user.groups),
                                "id",
                                flat=True,
                            )
                            allowed = await self.adapter.exists(
                                self.adapter.filter(
                                    self.AdminGroupPermission,
                                    group_id__in=group_ids,
                                    content_type_id=ct_id,
                                    action=action,
                                )
                            )
                if not allowed:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
            return user

        return _dep

    def build_auth_router(self, templates: Jinja2Templates) -> APIRouter:
        router = APIRouter()
        login_path = system_config.get_cached(SettingsKey.LOGIN_PATH, "/login")
        logout_path = system_config.get_cached(SettingsKey.LOGOUT_PATH, "/logout")
        setup_path = system_config.get_cached(SettingsKey.SETUP_PATH, "/setup")
        admin_prefix = system_config.get_cached(
            SettingsKey.ADMIN_PREFIX, settings.ADMIN_PATH
        )

        @router.get(login_path)
        async def login_form(request: Request):
            orm_prefix = await system_config.get(SettingsKey.ORM_PREFIX)
            settings_prefix = await system_config.get(SettingsKey.SETTINGS_PREFIX)
            views_prefix = await system_config.get(SettingsKey.VIEWS_PREFIX)
            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "error": None,
                    "prefix": admin_prefix,
                    "ORM_PREFIX": orm_prefix,
                    "SETTINGS_PREFIX": settings_prefix,
                    "VIEWS_PREFIX": views_prefix,
                    "site_title": self.site_title,
                    "brand_icon": self.brand_icon,
                },
            )

        @router.post(login_path)
        async def login_post(
            request: Request, username: str = Form(...), password: str = Form(...)
        ):
            user = await self.auth_service.authenticate_user(username, password)
            if not user:
                orm_prefix = await system_config.get(SettingsKey.ORM_PREFIX)
                settings_prefix = await system_config.get(SettingsKey.SETTINGS_PREFIX)
                views_prefix = await system_config.get(SettingsKey.VIEWS_PREFIX)
                return templates.TemplateResponse(
                    "pages/login.html",
                    {
                        "request": request,
                        "error": "Invalid credentials",
                        "prefix": admin_prefix,
                        "ORM_PREFIX": orm_prefix,
                        "SETTINGS_PREFIX": settings_prefix,
                        "VIEWS_PREFIX": views_prefix,
                        "site_title": self.site_title,
                        "brand_icon": self.brand_icon,
                    },
                    status_code=400,
                )
            session_key = await system_config.get(SettingsKey.SESSION_KEY)
            request.session[session_key] = str(user.id)
            return RedirectResponse(f"{admin_prefix}/", status_code=303)

        @router.get(logout_path)
        async def logout(request: Request):
            session_key = await system_config.get(SettingsKey.SESSION_KEY)
            request.session.pop(session_key, None)
            login_path = await system_config.get(SettingsKey.LOGIN_PATH)
            return RedirectResponse(
                f"{admin_prefix}{login_path}", status_code=303
            )

        @router.get(setup_path)
        async def setup_form(request: Request):
            if await self.auth_service.superuser_exists():
                login_path = await system_config.get(SettingsKey.LOGIN_PATH)
                return RedirectResponse(
                    f"{admin_prefix}{login_path}", status_code=303
                )
            orm_prefix = await system_config.get(SettingsKey.ORM_PREFIX)
            settings_prefix = await system_config.get(SettingsKey.SETTINGS_PREFIX)
            views_prefix = await system_config.get(SettingsKey.VIEWS_PREFIX)
            return templates.TemplateResponse(
                "pages/setup.html",
                {
                    "request": request,
                    "error": None,
                    "prefix": admin_prefix,
                    "ORM_PREFIX": orm_prefix,
                    "SETTINGS_PREFIX": settings_prefix,
                    "VIEWS_PREFIX": views_prefix,
                    "site_title": self.site_title,
                    "brand_icon": self.brand_icon,
                },
            )

        @router.post(setup_path)
        async def setup_post(
            request: Request,
            username: str = Form(...),
            email: str = Form(""),
            password: str = Form(...),
        ):
            if await self.auth_service.superuser_exists():
                login_path = await system_config.get(SettingsKey.LOGIN_PATH)
                return RedirectResponse(
                    f"{admin_prefix}{login_path}", status_code=303
                )
            user = await self.auth_service.create_superuser(
                username=username, email=email, password=password
            )
            session_key = await system_config.get(SettingsKey.SESSION_KEY)
            request.session[session_key] = str(user.id)
            return RedirectResponse(f"{admin_prefix}/", status_code=303)

        return router


from ..boot import admin as boot_admin

auth_service = AuthService(boot_admin.adapter)
admin_auth_service = AdminAuthService(auth_service, boot_admin.adapter)

# The End

