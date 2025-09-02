# -*- coding: utf-8 -*-
"""
services

Service layer for admin CRUD operations.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from .actions.builder import ScopeQueryBuilder
from .auth import AdminUserDTO
from .exceptions import (
    ActionNotFound,
    PermissionDenied,
    AdminIntegrityError,
    BadRequestError,
    NotFoundError,
    PermissionError,
)
from .filters import FilterSpec
from .permissions import permissions_service
from .settings import SettingsKey, system_config
from .base import BaseModelAdmin


class ObjectNotFoundError(Exception):
    """Fallback when the adapter lacks a ``DoesNotExist`` exception."""


class DataIntegrityError(Exception):
    """Fallback when the adapter lacks an ``IntegrityError`` exception."""


class AdminService:
    """Encapsulate CRUD operations for ``ModelAdmin`` instances."""

    class ParamsValidator:
        """Validate action parameters against a schema."""

        def validate(self, schema: dict, params: dict) -> None:
            for name, typ in schema.items():
                if name not in params:
                    raise BadRequestError(f"Missing param '{name}'")
                if not isinstance(params[name], typ):
                    raise BadRequestError(f"Invalid type for param '{name}'")
            for name in params:
                if name not in schema:
                    raise BadRequestError(f"Unexpected param '{name}'")

    def __init__(self, admin: BaseModelAdmin):
        self.admin = admin
        self.adapter = admin.adapter
        self.md = self.adapter.get_model_descriptor(admin.model)
        self.DoesNotExist = getattr(self.adapter, "DoesNotExist", ObjectNotFoundError)
        self.IntegrityError = getattr(self.adapter, "IntegrityError", DataIntegrityError)

    async def get_object(self, request, user: AdminUserDTO, pk: str):
        qs = self.admin.get_objects(request, user)
        try:
            return await self.adapter.get(qs, **{self.md.pk_attr: pk})
        except self.DoesNotExist:
            raise NotFoundError()

    async def list_data(
        self,
        request,
        user: AdminUserDTO,
        search: str,
        page_num: int,
        per_page: int | None,
        order: str,
    ) -> Dict[str, Any]:
        columns = self.admin.get_list_columns(self.md)
        params: Dict[str, Any] = {"search": search, "order": order}
        qs = self.admin.get_list_queryset(request, user, self.md, params)
        order = params.get("order", order)

        if per_page is None:
            per_page = await system_config.get(SettingsKey.DEFAULT_PER_PAGE)
        max_per_page = await system_config.get(SettingsKey.MAX_PER_PAGE)
        per_page = max(1, min(int(per_page), max_per_page))
        page_num = max(1, int(page_num))
        total = await self.adapter.count(qs)
        pages = max(1, (total + per_page - 1) // per_page)
        offset = (page_num - 1) * per_page
        qs = self.adapter.limit(self.adapter.offset(qs, offset), per_page)
        objs = await self.adapter.fetch_all(qs)
        items = []
        for o in objs:
            row = await self.admin.serialize_list_row(o, self.md, columns)
            row["can_change"] = self.admin.allow(user, "change", o)
            row["can_delete"] = self.admin.allow(user, "delete", o)
            items.append(row)

        return {
            "columns": columns,
            "columns_meta": self.admin.columns_meta(self.md, columns),
            "id_field": "row_pk",
            "items": items,
            "page": page_num,
            "pages": pages,
            "per_page": per_page,
            "total": total,
            "order": order,
        }

    async def run_action(
        self,
        request,
        user: AdminUserDTO,
        name: str,
        payload: dict,
        app_label: str,
        model_name: str,
    ) -> Dict[str, Any]:
        action_obj = self.admin.get_action(name)
        if action_obj is None:
            raise NotFoundError("Action not found")
        spec = action_obj.spec
        allowed_scope = spec.scope or []
        if ("ids" in payload and "ids" not in allowed_scope) or (
            "query" in payload and "query" not in allowed_scope
        ):
            raise BadRequestError("Invalid scope type")
        required_perm = spec.required_perm
        if required_perm:
            await permissions_service.require_model_permission(
                required_perm, app_value=app_label, model_value=model_name
            )(request)

        params = payload.get("params", {})
        params_validator = self.ParamsValidator()
        params_validator.validate(spec.params_schema or {}, params)
        qs = self.admin.get_objects(request, user)

        ids = payload.get("ids")
        if ids is not None:
            qs = self.adapter.apply_filter_spec(
                qs, [FilterSpec(self.md.pk_attr, "in", ids)]
            )
        else:
            query = payload.get("query")
            if query is not None:
                builder = ScopeQueryBuilder(
                    self.admin, self.md, user, self.adapter.QuerySet
                )
                qs = builder.build(query)

        try:
            result = await self.admin.perform_action(name, qs, params, user)
        except ActionNotFound as exc:
            raise NotFoundError(str(exc)) from exc
        except PermissionDenied as exc:
            raise PermissionError(str(exc)) from exc
        return asdict(result)

    async def create(
        self, request, user: AdminUserDTO, payload: dict
    ) -> Dict[str, Any]:
        if not self.admin.allow(user, "add", None):
            raise PermissionError("Add not allowed by business rule")
        try:
            obj = await self.admin.create(request, user, self.md, payload)
            return {"ok": True, "id": getattr(obj, self.md.pk_attr)}
        except self.IntegrityError as exc:
            try:
                self.admin.handle_integrity_error(exc)
            except AdminIntegrityError as err:
                raise BadRequestError(str(err)) from err

    async def update(
        self, request, user: AdminUserDTO, pk: str, payload: dict
    ) -> Dict[str, Any]:
        try:
            obj = await self.get_object(request, user, pk)
        except self.DoesNotExist:
            raise NotFoundError()
        if not self.admin.allow(user, "change", obj):
            raise PermissionError("Change not allowed by business rule")
        try:
            await self.admin.update(request, user, self.md, obj, payload)
            return {"ok": True}
        except self.IntegrityError as exc:
            try:
                self.admin.handle_integrity_error(exc)
            except AdminIntegrityError as err:
                raise BadRequestError(str(err)) from err

    async def delete(
        self, request, user: AdminUserDTO, pk: str
    ) -> Dict[str, Any]:
        try:
            obj = await self.get_object(request, user, pk)
        except self.DoesNotExist:
            raise NotFoundError()
        if not self.admin.allow(user, "delete", obj):
            raise PermissionError("Delete not allowed by business rule")
        delete_method = getattr(self.admin, "delete", None)
        if delete_method:
            await delete_method(request, user, self.md, obj)
        else:
            await self.adapter.delete(obj)
        return {"ok": True}

# The End

