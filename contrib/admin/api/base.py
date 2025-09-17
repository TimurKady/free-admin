# -*- coding: utf-8 -*-
"""
base

API endpoints for the admin interface.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from config.settings import settings

from ..adapters import BaseAdapter
from ..boot import admin as boot_admin
from ..core.services.auth import AdminUserDTO
from ..core.services import PermAction, permissions_service, ScopeQueryService
from ..core.services.tokens import ScopeTokenService

from ..core.exceptions import (
    ActionNotFound,
    PermissionDenied,
    AdminModelNotFound,
    HTTPError,
)
from ..core.settings import SettingsKey, system_config
from ..runner import admin_action_runner


class AdminAPI:
    """API endpoints for the admin interface."""

    class ParamsValidator:
        """Validate action parameters against a schema.

        Boolean parameters accept only ``true``/``false``.
        """

        def validate(self, schema: dict, params: dict) -> None:
            for name, typ in schema.items():
                if name not in params:
                    raise HTTPException(status_code=400, detail=f"Missing param '{name}'")
                if typ is bool:
                    if type(params[name]) is not bool:
                        raise HTTPException(status_code=400, detail=f"Invalid type for param '{name}'")
                elif not isinstance(params[name], typ):
                    raise HTTPException(status_code=400, detail=f"Invalid type for param '{name}'")
            for name in params:
                if name not in schema:
                    raise HTTPException(status_code=400, detail=f"Unexpected param '{name}'")

    def __init__(self, adapter: BaseAdapter | None = None) -> None:
        """Initialize API endpoints for the admin interface."""

        self.logger = logging.getLogger(__name__)
        self.adapter = adapter or boot_admin.adapter
        self.DoesNotExist = getattr(self.adapter, "DoesNotExist", Exception)

        self.API_PREFIX = system_config.get_cached(SettingsKey.API_PREFIX, "/api")

        schema_rel = system_config.get_cached(SettingsKey.API_SCHEMA, "/schema")
        list_filters_rel = system_config.get_cached(
            SettingsKey.API_LIST_FILTERS, "/list_filters"
        )
        lookup_rel = system_config.get_cached(SettingsKey.API_LOOKUP, "/lookup")

        self.SCHEMA_PATH = self._abs(schema_rel)
        self.LIST_FILTERS_PATH = self._abs(list_filters_rel)
        self.LOOKUP_PATH = self._abs(lookup_rel)
        self.ACTIONS_PATH = self._abs("/action")

        self.router = APIRouter()
        self.scope_token_service = ScopeTokenService()
        self.scope_query_service = ScopeQueryService(self.adapter)
        self.params_validator = self.ParamsValidator()

        self.router.get(
            self._relative(self.SCHEMA_PATH), name="admin.api.schema"
        )(self.api_schema)
        self.router.get(
            self._relative(self.LIST_FILTERS_PATH), name="admin.api.list_filters"
        )(self.api_list_filters)
        self.router.get(
            f"{self._relative(self.LOOKUP_PATH)}/{{app}}/{{model}}/{{field}}",
            name="admin.api.lookup",
        )(self.api_lookup)
        self.router.get(
            f"{self._relative(self.ACTIONS_PATH)}/{{app}}.{{model}}/list",
            name="admin.api.actions_list",
        )(self.actions_list)
        self.router.post(
            f"{self._relative(self.ACTIONS_PATH)}/{{app}}.{{model}}/preview",
            name="admin.api.actions_preview",
        )(self.actions_preview)
        self.router.post(
            f"{self._relative(self.ACTIONS_PATH)}/{{app}}.{{model}}/{{action}}",
            name="admin.api.action_run",
        )(self.action_run)

        self.router.post(
            f"{self._relative(self.ACTIONS_PATH)}/{{app}}.{{model}}/token",
            name="admin.api.scope_token",
        )(self.scope_token)


    def _abs(self, path: str) -> str:
        if path.startswith(self.API_PREFIX):
            return path
        return f"{self.API_PREFIX}{path}"

    def _relative(self, path: str) -> str:
        """Return a path relative to ``API_PREFIX`` suitable for the router."""

        if path.startswith(self.API_PREFIX):
            path = path[len(self.API_PREFIX) :]
        if not path.startswith("/"):
            path = "/" + path
        return path

    def _get_admin(self, admin_site, app: str, model: str):
        try:
            return admin_site.find_admin_or_404(app, model)
        except AdminModelNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def api_schema(
        self,
        request: Request,
        app: str,
        model: str,
        mode: Literal["add", "edit"] = "add",
        pk: str | None = None,
        user: AdminUserDTO = Depends(
            permissions_service.require_model_permission(PermAction.view)
        ),
    ):
        admin_site = request.app.state.admin_site
        admin = self._get_admin(admin_site, app, model)

        md = self.adapter.get_model_descriptor(admin.model)

        obj = None
        if mode == "edit" and pk is not None:
            qs = admin.get_objects(request, user)
            try:
                obj = await self.adapter.get(qs, **{md.pk_attr: pk})
            except self.DoesNotExist:
                raise HTTPException(status_code=404)

        try:
            schema_data = await admin.get_schema(request, user, md, mode, obj=obj)
        except Exception as exc:  # pragma: no cover - defensive
            field = str(exc) or "unknown"
            self.logger.exception(
                "api_schema failed for %s.%s", app, model
            )
            raise HTTPException(
                status_code=400,
                detail=f"Unknown relation target for field {field}",
            ) from exc

        return {
            "schema": schema_data["schema"],
            "startval": schema_data["startval"],
        }

    async def api_list_filters(
        self,
        request: Request,
        app: str,
        model: str,
        user: AdminUserDTO = Depends(
            permissions_service.require_model_permission(PermAction.view)
        ),
    ):
        admin_site = request.app.state.admin_site
        admin = self._get_admin(admin_site, app, model)
        md = self.adapter.get_model_descriptor(admin.model)

        return {"filters": admin.get_list_filters(md)}

    async def api_lookup(
        self,
        request: Request,
        app: str,
        model: str,
        field: str,
        q: str = "",
        page: int = 1,
        pk: str | None = None,
        user: AdminUserDTO = Depends(
            permissions_service.require_model_permission(PermAction.view)
        ),
    ):
        """Return relation choices for ``field`` as structured JSON.

        Parameters:
            request: Incoming request instance.
            app: Application label of the model.
            model: Model name inside the application.
            field: Field name requiring lookup.
            q: Optional search query (currently ignored).
            page: Page number for pagination (currently ignored).
            pk: Optional primary key of the instance to extract current value
                from.
            user: Authenticated admin user.
        Returns:
            Mapping containing ``placeholder``, ``default``, ``value`` and
            ``results`` where each result entry has ``id`` and ``title`` keys.
        """

        admin_site = request.app.state.admin_site
        admin = self._get_admin(admin_site, app, model)
        md = self.adapter.get_model_descriptor(admin.model)
        fd = md.fields_map.get(field)
        rel = getattr(fd, "relation", None)
        if not fd or not rel or rel.kind not in {"fk", "m2m"}:
            raise HTTPException(status_code=404)
        rel_model = self.adapter.get_model(rel.target)
        if rel_model is None:
            raise HTTPException(status_code=404)

        # Load available choices for the relation
        pairs = await admin.get_choices(fd)
        meta = getattr(fd, "meta", {}) or {}

        # Determine default identifier from the field descriptor
        raw_default = getattr(fd, "default", None)
        if callable(raw_default):
            raw_default = raw_default()
        is_many = bool(getattr(fd, "many", False) or rel.kind == "m2m")
        if raw_default is not None:
            if is_many:
                if isinstance(raw_default, (list, tuple, set)):
                    default_id = [str(v) for v in raw_default]
                else:
                    default_id = [str(raw_default)]
            else:
                default_id = str(raw_default)
        else:
            default_id = [] if is_many else None

        # Extract current value identifiers from the instance when available
        value: list[str] | str | None
        value = [] if is_many else None
        if pk is not None:
            qs = admin.get_objects(request, user)
            try:
                obj = await self.adapter.get(qs, **{md.pk_attr: pk})
            except self.DoesNotExist:
                obj = None
            if obj is not None:
                if is_many:
                    try:
                        related = await getattr(obj, field).all()
                    except Exception:  # pragma: no cover - defensive
                        related = []
                    value = [str(getattr(o, "pk", o)) for o in related]
                else:
                    cur = getattr(obj, f"{field}_id", None)
                    if cur is not None:
                        value = str(cur)

        results = [{"id": pk, "title": label} for pk, label in pairs]
        return {
            "placeholder": meta.get("placeholder"),
            "default": default_id,
            "value": value,
            "results": results,
        }

    async def actions_list(
        self,
        request: Request,
        app: str,
        model: str,
        user: AdminUserDTO = Depends(
            permissions_service.require_model_permission(PermAction.view)
        ),
    ):
        admin_site = request.app.state.admin_site
        admin = self._get_admin(admin_site, app, model)
        return admin.get_action_specs(user)

    async def actions_preview(
        self,
        request: Request,
        app: str,
        model: str,
        payload: dict = Body(...),
        user: AdminUserDTO = Depends(
            permissions_service.require_model_permission(PermAction.view)
        ),
    ):
        admin_site = request.app.state.admin_site
        admin = self._get_admin(admin_site, app, model)
        md = self.adapter.get_model_descriptor(admin.model)
        scope = payload.get("scope")
        if scope is None:
            raise HTTPException(status_code=400, detail="Missing scope")
        try:
            qs = self.scope_query_service.build_queryset(
                admin, md, request, user, scope
            )
        except HTTPError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        return {"count": await self.adapter.count(qs)}

    async def action_run(
        self,
        request: Request,
        app: str,
        model: str,
        action: str,
        payload: dict = Body(...),
        user: AdminUserDTO = Depends(
            permissions_service.require_model_permission(PermAction.view)
        ),
    ):
        admin_site = request.app.state.admin_site
        admin = self._get_admin(admin_site, app, model)

        action_obj = admin.get_action(action)
        if action_obj is None:
            raise HTTPException(status_code=404)
        spec = action_obj.spec
        if spec.required_perm:
            await permissions_service.require_model_permission(
                spec.required_perm, app_value=app, model_value=model, admin_site=admin_site
            )(request)

        md = self.adapter.get_model_descriptor(admin.model)
        scope = payload.get("scope")
        if scope is None:
            token = payload.get("scope_token")
            if token is None:
                raise HTTPException(status_code=400, detail="Missing scope")
            try:
                scope = self.scope_token_service.verify(token)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid scope_token")
        scope_type = scope.get("type")
        if spec.scope and scope_type not in spec.scope:
            raise HTTPException(status_code=400, detail="Scope type not allowed")
        qs = self.scope_query_service.build_queryset(
            admin, md, request, user, scope
        )
        params = payload.get("params", {})
        self.params_validator.validate(spec.params_schema, params)
        affected = await self.adapter.count(qs)
        batch_size = system_config.get_cached(
            SettingsKey.ACTION_BATCH_SIZE, settings.ACTION_BATCH_SIZE
        )
        if affected > batch_size:
            asyncio.create_task(
                admin_action_runner.run(
                    app, model, action, scope, params, user, admin_site=admin_site
                )
            )
            return {"ok": True, "background": True}
        try:
            return await admin_action_runner.run(
                app, model, action, scope, params, user, admin_site=admin_site
            )
        except ActionNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PermissionDenied as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except HTTPError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    async def scope_token(
        self,
        request: Request,
        app: str,
        model: str,
        payload: dict = Body(...),
        user: AdminUserDTO = Depends(
            permissions_service.require_model_permission(PermAction.view)
        ),
    ):
        admin_site = request.app.state.admin_site
        admin = self._get_admin(admin_site, app, model)
        md = self.adapter.get_model_descriptor(admin.model)
        scope = payload.get("scope")
        if scope is None:
            raise HTTPException(status_code=400, detail="Missing scope")
        try:
            _ = self.scope_query_service.build_queryset(
                admin, md, request, user, scope
            )
        except HTTPError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        ttl = int(payload.get("ttl", 60))
        token = self.scope_token_service.sign(scope, ttl)
        return {"scope_token": token}

_api = AdminAPI()
router = _api.router
API_PREFIX = _api.API_PREFIX

__all__ = ["AdminAPI", "router", "API_PREFIX"]

# The End

