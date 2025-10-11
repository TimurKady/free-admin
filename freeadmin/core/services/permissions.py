# -*- coding: utf-8 -*-
"""
permissions

Permission checks based on flat user/group tables.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Awaitable, Callable, Any

from fastapi import HTTPException, status
from fastapi.requests import Request

from ...adapters import BaseAdapter
from ..auth import admin_auth_service

if TYPE_CHECKING:  # pragma: no cover - for type checking only
    from .auth import AdminUserDTO
    from ..site import AdminSite


class PermissionsService:
    """Check user permissions against configured actions."""

    def __init__(self, adapter: BaseAdapter) -> None:
        """Initialize the service with the given adapter."""
        self.adapter = adapter
        self.AdminUser = adapter.user_model
        self.AdminUserPermission = adapter.user_permission_model
        self.AdminGroupPermission = adapter.group_permission_model
        self.PermAction = adapter.perm_action
        self.logger = logging.getLogger(__name__)

    async def _get_group_ids(self, user: Any) -> list[int]:
        groups_qs = self.adapter.all(user.groups)
        return await self.adapter.fetch_values(groups_qs, "id", flat=True)

    async def _has_permission(
        self, user: Any, action: "PermAction", ct_id: int | None
    ) -> bool:
        if not (user.is_active and user.is_staff):
            return False
        if user.is_superuser:
            return True
        allowed = await self.adapter.exists(
            self.adapter.filter(
                self.AdminUserPermission,
                user_id=user.id,
                content_type_id=ct_id,
                action=action,
            )
        )
        if allowed:
            return True
        group_ids = await self._get_group_ids(user)
        return await self.adapter.exists(
            self.adapter.filter(
                self.AdminGroupPermission,
                group_id__in=group_ids,
                content_type_id=ct_id,
                action=action,
            )
        )

    def require_model_permission(
        self,
        action: "PermAction",
        app_param: str = "app",
        model_param: str = "model",
        app_value: str | None = None,
        model_value: str | None = None,
        admin_site: "AdminSite | None" = None,
    ) -> Callable[[Request], Awaitable[AdminUserDTO]]:
        """Dependency ensuring user has ``action`` permission on a model.

        ``app`` and ``model`` may be provided as path or query parameters.
        Alternatively ``app_value`` and ``model_value`` can explicitly define the
        target model. Returns the current user as ``AdminUserDTO`` when permission
        check passes.
        """

        async def _dep(request: Request) -> AdminUserDTO:
            site = admin_site or getattr(request.app.state, "admin_site", None)
            if site is None:
                raise HTTPException(status_code=500, detail="Admin site not configured")

            user_dto = await admin_auth_service.get_current_admin_user(request)
            orm_user = request.state.user

            app = (
                app_value
                or request.path_params.get(app_param)
                or request.query_params.get(app_param)
            )
            model = (
                model_value
                or request.path_params.get(model_param)
                or request.query_params.get(model_param)
            )
            if not app or not model:
                raise HTTPException(status_code=400, detail="Missing app/model params")

            ct_id = site.get_ct_id(app, model)
            if ct_id is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Unknown content type: {app}.{model}",
                )

            if not await self._has_permission(orm_user, action, ct_id):
                self.logger.debug(
                    "Permission denied",
                    extra={"user_id": orm_user.id, "ct_id": ct_id, "action": action},
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied"
                )
            return user_dto

        return _dep

    def require_global_permission(
        self, action: "PermAction"
    ) -> Callable[[Request], Awaitable[None]]:
        """Dependency for global pages (Settings, etc.)."""

        async def _dep(request: Request) -> None:
            user = getattr(request.state, "user", None)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth required"
                )

            if not await self._has_permission(user, action, None):
                self.logger.debug(
                    "Permission denied",
                    extra={"user_id": user.id, "ct_id": None, "action": action},
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied"
                )
            return None

        return _dep


from ...boot import admin as boot_admin

permissions_service = PermissionsService(boot_admin.adapter)
PermAction = permissions_service.PermAction

__all__ = ["PermAction", "PermissionsService", "permissions_service"]

# The End

