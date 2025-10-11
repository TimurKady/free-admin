# -*- coding: utf-8 -*-
"""
permissions

Permission checks based on flat user/group tables.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Awaitable, Callable, Any

from fastapi import HTTPException, status
from fastapi.requests import Request

from ...adapters import BaseAdapter
from ..auth import admin_auth_service
from ..cache.permissions import SQLitePermissionCache

if TYPE_CHECKING:  # pragma: no cover - for type checking only
    from .auth import AdminUserDTO
    from ..site import AdminSite


class PermissionsService:
    """Check user permissions against configured actions."""

    def __init__(
        self,
        adapter: BaseAdapter,
        *,
        cache_path: str | None = None,
        cache_ttl: timedelta | None = None,
        prune_interval: timedelta | None = None,
    ) -> None:
        """Initialize the service with the given adapter."""

        self.adapter = adapter
        self.AdminUser = adapter.user_model
        self.AdminGroup = adapter.group_model
        self.AdminUserPermission = adapter.user_permission_model
        self.AdminGroupPermission = adapter.group_permission_model
        self.PermAction = adapter.perm_action
        self.logger = logging.getLogger(__name__)
        self._cache_ttl = cache_ttl or timedelta(minutes=5)
        self._permission_cache = SQLitePermissionCache(
            path=cache_path, ttl=self._cache_ttl
        )
        interval = prune_interval or self._cache_ttl
        if interval <= timedelta(0):
            interval = self._cache_ttl
        self._prune_interval = interval
        self._next_prune_at = datetime.now(timezone.utc) + self._prune_interval
        self._prune_task: asyncio.Task[int] | None = None
        self._user_invalidation_hooks: list[Callable[[str], Awaitable[None] | None]] = []
        self._permission_snapshot = datetime.now(timezone.utc)

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

        user_key = str(getattr(user, "id"))
        ct_key = self._normalize_content_type_id(ct_id)
        action_value = self._normalize_action(action)

        cached = await asyncio.to_thread(
            self._permission_cache.get_permission, user_key, ct_key, action_value
        )
        if cached is not None:
            return cached

        allowed = await self.adapter.exists(
            self.adapter.filter(
                self.AdminUserPermission,
                user_id=user.id,
                content_type_id=ct_id,
                action=action,
            )
        )
        if not allowed:
            group_ids = await self._get_group_ids(user)
            if group_ids:
                allowed = await self.adapter.exists(
                    self.adapter.filter(
                        self.AdminGroupPermission,
                        group_id__in=group_ids,
                        content_type_id=ct_id,
                        action=action,
                    )
                )

        try:
            await asyncio.to_thread(
                self._permission_cache.store_permission,
                user_key,
                ct_key,
                action_value,
                allowed,
            )
        except Exception:  # pragma: no cover - defensive logging
            self.logger.exception("Failed to store permission cache entry")
        else:
            self._maybe_schedule_prune()

        return allowed

    async def invalidate_user_permissions(self, user_id: int | str) -> None:
        """Remove cached permission outcomes for ``user_id``."""

        user_key = str(user_id)
        await asyncio.to_thread(
            self._permission_cache.invalidate_user, user_key
        )
        self._touch_permission_snapshot()
        await self._notify_user_invalidation(user_key)

    async def invalidate_group_permissions(self, group_id: int | str) -> None:
        """Remove cached permissions for members belonging to ``group_id``."""

        try:
            group = await self.adapter.get(self.AdminGroup, id=group_id)
        except Exception:  # pragma: no cover - adapter specific exceptions
            self.logger.debug(
                "Skipping permission cache invalidation for missing group %s", group_id
            )
            return

        users_qs = self.adapter.all(group.users)
        member_ids = await self.adapter.fetch_values(users_qs, "id", flat=True)
        if not member_ids:
            return
        member_tokens = [str(member) for member in member_ids]
        await asyncio.to_thread(
            self._permission_cache.invalidate_group,
            str(group_id),
            member_tokens,
        )
        self._touch_permission_snapshot()
        for member in member_tokens:
            await self._notify_user_invalidation(member)

    def _normalize_action(self, action: "PermAction" | str) -> str:
        value = getattr(action, "value", action)
        return str(value)

    def _normalize_content_type_id(self, ct_id: int | None) -> str:
        return str(ct_id) if ct_id is not None else "*"

    def _maybe_schedule_prune(self) -> None:
        now = datetime.now(timezone.utc)
        if now < self._next_prune_at:
            return
        if self._prune_task is not None and not self._prune_task.done():
            return
        self._next_prune_at = now + self._prune_interval
        loop = asyncio.get_running_loop()
        task = loop.create_task(
            asyncio.to_thread(self._permission_cache.prune_expired)
        )
        task.add_done_callback(self._handle_prune_result)
        self._prune_task = task

    def _handle_prune_result(self, task: asyncio.Task[int]) -> None:
        try:
            removed = task.result()
            if removed:
                self.logger.debug(
                    "Pruned %s expired permission cache entries", removed
                )
        except Exception:  # pragma: no cover - defensive logging
            self.logger.exception("Failed pruning permission cache")

    def register_user_invalidation_hook(
        self, callback: Callable[[str], Awaitable[None] | None]
    ) -> None:
        """Register ``callback`` invoked whenever a user cache is invalidated."""

        if callback not in self._user_invalidation_hooks:
            self._user_invalidation_hooks.append(callback)

    def get_permission_snapshot(self) -> datetime:
        """Return the timestamp representing the latest invalidation."""

        return self._permission_snapshot

    async def _notify_user_invalidation(self, user_id: str) -> None:
        if not self._user_invalidation_hooks:
            return
        for hook in list(self._user_invalidation_hooks):
            try:
                result = hook(user_id)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to propagate permission invalidation for user %s", user_id
                )

    def _touch_permission_snapshot(self) -> datetime:
        snapshot = datetime.now(timezone.utc)
        self._permission_snapshot = snapshot
        return snapshot

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

