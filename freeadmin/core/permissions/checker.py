# -*- coding: utf-8 -*-
"""
checker

Centralized permission checks for admin site resources.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, TYPE_CHECKING

from fastapi import HTTPException, Request, status

from ..auth import admin_auth_service
from ..exceptions import AdminModelNotFound, PermissionDenied
from ..services.permissions import PermAction, PermissionsService, permissions_service

if TYPE_CHECKING:  # pragma: no cover - for type checking only
    from ..services.auth import AdminUserDTO
    from ..site import AdminSite


class PermissionChecker:
    """Provide a unified interface for permission validation."""

    def __init__(
        self,
        service: PermissionsService,
        *,
        admin_site: "AdminSite | None" = None,
    ) -> None:
        """Initialize the checker with underlying permission service."""

        self._service = service
        self._admin_site = admin_site
        self.PermAction = service.PermAction
        self.logger = logging.getLogger(__name__)

    def bind_to(self, admin_site: "AdminSite") -> "PermissionChecker":
        """Return a checker bound to the specified admin site."""

        return PermissionChecker(self._service, admin_site=admin_site)

    def register_user_invalidation_hook(
        self, callback: Callable[[str], Awaitable[None] | None]
    ) -> None:
        """Register ``callback`` invoked when permission caches invalidate."""

        register = getattr(self._service, "register_user_invalidation_hook", None)
        if callable(register):
            register(callback)

    def get_permission_snapshot(self):
        """Return timestamp representing the current permission snapshot."""

        getter = getattr(self._service, "get_permission_snapshot", None)
        if callable(getter):
            return getter()
        return None

    async def check_model(
        self,
        user: Any,
        app_label: str,
        model_name: str,
        action: PermAction,
        *,
        admin_site: "AdminSite | None" = None,
    ) -> bool:
        """Verify ``user`` may execute ``action`` on ``app_label.model_name``."""

        site = self._resolve_admin_site(admin_site)
        ct_id = site.get_ct_id(app_label, model_name)
        if ct_id is None:
            raise AdminModelNotFound(f"Unknown content type: {app_label}.{model_name}")
        allowed = await self._service._has_permission(user, action, ct_id)
        if not allowed:
            raise PermissionDenied("Permission denied")
        return True

    async def check_view(
        self,
        user: Any,
        action: PermAction,
        *,
        dotted: str | None = None,
        app: str | None = None,
        slug: str | None = None,
        view_key: str | None = None,
        admin_site: "AdminSite | None" = None,
    ) -> bool:
        """Ensure ``user`` has ``action`` access for the resolved view."""

        site = self._resolve_admin_site(admin_site)
        resolved_dotted = dotted
        if resolved_dotted is None and app is not None and slug is not None:
            virtual = site.registry.get_view_virtual(app, slug)
            if virtual is not None:
                resolved_dotted = virtual.dotted
        if resolved_dotted is None and view_key is not None:
            virtual = site.registry.get_view_virtual_by_path(view_key)
            if virtual is not None:
                resolved_dotted = virtual.dotted
        if resolved_dotted is None:
            allowed = await self._service._has_permission(user, action, None)
            if not allowed:
                raise PermissionDenied("Permission denied")
            return True
        if getattr(user, "is_superuser", False):
            return True
        ct_id = site.get_ct_id_by_dotted(resolved_dotted)
        if ct_id is None:
            raise PermissionDenied("Permission denied")
        allowed = await self._service._has_permission(user, action, ct_id)
        if not allowed:
            raise PermissionDenied("Permission denied")
        return True

    async def check_card(
        self,
        user: Any,
        card_key: str,
        action: PermAction,
        *,
        admin_site: "AdminSite | None" = None,
    ) -> bool:
        """Validate that ``user`` may interact with card ``card_key``."""

        site = self._resolve_admin_site(admin_site)
        site.cards.get_card(card_key)
        virtual = site.cards.get_card_virtual(card_key)
        if getattr(user, "is_superuser", False):
            return True
        ct_id = site.get_ct_id_by_dotted(virtual.dotted)
        if ct_id is None:
            raise PermissionDenied("Permission denied")
        allowed = await self._service._has_permission(user, action, ct_id)
        if not allowed:
            raise PermissionDenied("Permission denied")
        return True

    def require_model(
        self,
        action: PermAction,
        *,
        app_param: str = "app",
        model_param: str = "model",
        app_value: str | None = None,
        model_value: str | None = None,
        admin_site: "AdminSite | None" = None,
    ) -> Callable[[Request], Awaitable["AdminUserDTO"]]:
        """Return dependency enforcing model-level access for ``action``."""

        async def dependency(request: Request) -> "AdminUserDTO":
            site = self._resolve_admin_site(admin_site or getattr(request.app.state, "admin_site", None))
            user_dto = await admin_auth_service.get_current_admin_user(request)
            orm_user = getattr(request.state, "user", None)
            if orm_user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth required")
            app = app_value or request.path_params.get(app_param) or request.query_params.get(app_param)
            model = (
                model_value
                or request.path_params.get(model_param)
                or request.query_params.get(model_param)
            )
            if not app or not model:
                raise HTTPException(status_code=400, detail="Missing app/model params")
            try:
                await self.check_model(orm_user, app, model, action, admin_site=site)
            except AdminModelNotFound as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            except PermissionDenied as exc:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
            return user_dto

        return dependency

    def require_view(
        self,
        action: PermAction,
        *,
        dotted: str | None = None,
        app: str | None = None,
        slug: str | None = None,
        view_key: str | None = None,
        admin_site: "AdminSite | None" = None,
    ) -> Callable[[Request], Awaitable[None]]:
        """Return dependency validating ``action`` access for a view."""

        async def dependency(request: Request) -> None:
            site = self._resolve_admin_site(admin_site or getattr(request.app.state, "admin_site", None))
            user = getattr(request.state, "user", None)
            if user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth required")
            key = view_key or request.url.path.rstrip("/") or "/"
            try:
                await self.check_view(
                    user,
                    action,
                    dotted=dotted,
                    app=app,
                    slug=slug,
                    view_key=key,
                    admin_site=site,
                )
            except PermissionDenied as exc:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
            return None

        return dependency

    def require_card(
        self,
        action: PermAction,
        *,
        admin_site: "AdminSite | None" = None,
        key_param: str = "key",
    ) -> Callable[[Request], Awaitable[None]]:
        """Return dependency ensuring card access."""

        async def dependency(request: Request) -> None:
            site = self._resolve_admin_site(admin_site or getattr(request.app.state, "admin_site", None))
            await admin_auth_service.get_current_admin_user(request)
            orm_user = getattr(request.state, "user", None)
            if orm_user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth required")
            card_key = request.path_params.get(key_param)
            if not card_key:
                raise HTTPException(status_code=400, detail="Missing card key")
            try:
                await self.check_card(orm_user, card_key, action, admin_site=site)
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            except PermissionDenied as exc:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
            return None

        return dependency

    def _resolve_admin_site(self, admin_site: "AdminSite | None") -> "AdminSite":
        site = admin_site or self._admin_site
        if site is None:
            raise RuntimeError("Admin site not configured")
        return site


permission_checker = PermissionChecker(permissions_service)


# The End

