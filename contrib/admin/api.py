# -*- coding: utf-8 -*-
"""
API endpoints for the admin interface.
"""

from __future__ import annotations

from typing import Callable, Literal

from fastapi import APIRouter, Depends, Request

from .core.auth import AdminUserDTO
from .core.base import BaseModelAdmin
from .core.permissions import require_model_permission, PermAction
from .adapters.tortoise import get_model_descriptor
from .core.settings import SettingsKey, system_config


class ApiController:
    @staticmethod
    def attach(
        router: APIRouter,
        find_admin: Callable[[str, str], BaseModelAdmin],
    ) -> None:

        schema_path = system_config.get_cached(SettingsKey.API_SCHEMA, "/api/schema")
        uiconfig_path = system_config.get_cached(SettingsKey.API_UICONFIG, "/api/uiconfig")
        list_filters_path = system_config.get_cached(
            SettingsKey.API_LIST_FILTERS, "/api/list_filters"
        )
        autocomplete_path = system_config.get_cached(
            SettingsKey.API_AUTOCOMPLETE, "/api/autocomplete"
        )

        @router.get(schema_path, name="admin.api.schema")
        async def api_schema(
            request: Request,
            app: str,
            model: str,
            mode: Literal["add", "edit"] = "add",
            user: AdminUserDTO = Depends(require_model_permission(PermAction.view)),
        ):
            admin = find_admin(app, model)

            md = get_model_descriptor(admin.model)
            schema_data = await admin.get_schema(request, user, md, mode)

            return {
                "schema": schema_data["schema"],
                "startval": schema_data["startval"],
            }

        @router.get(uiconfig_path, name="admin.api.uiconfig")
        async def api_uiconfig(
            request: Request,
            app: str,
            model: str,
            user: AdminUserDTO = Depends(require_model_permission(PermAction.view)),
        ):
            admin = find_admin(app, model)

            md = get_model_descriptor(admin.model)
            ui_schema = await admin.build_ui(request, user, md, "add")

            return {
                "uiSchema": ui_schema,
                "widgets": {},
                "masks": {},
                "readonly_fields": getattr(admin, "readonly_fields", []),
                "hidden_fields": getattr(admin, "hidden_fields", []),
            }

        @router.get(list_filters_path, name="admin.api.list_filters")
        async def api_list_filters(
            request: Request,
            app: str,
            model: str,
            user: AdminUserDTO = Depends(require_model_permission(PermAction.view)),
        ):
            admin = find_admin(app, model)
            md = get_model_descriptor(admin.model)

            return {"filters": admin.get_list_filters(md)}

        @router.get(autocomplete_path, name="admin.api.autocomplete")
        async def api_autocomplete(
            request: Request,
            app: str,
            model: str,
            field: str,
            q: str = "",
            page: int = 1,
            per_page: int | None = None,
            user: AdminUserDTO = Depends(require_model_permission(PermAction.view)),
        ):
            admin = find_admin(app, model)
            if per_page is None:
                per_page = await system_config.get(SettingsKey.DEFAULT_PER_PAGE)
            md = get_model_descriptor(admin.model)
            fd = md.field(field)
            if not fd or not fd.relation:
                return {"results": [], "page": 1, "pages": 1, "total": 0}

            from tortoise import Tortoise

            if hasattr(Tortoise, "get_model"):
                rel_model = Tortoise.get_model(fd.relation.target)
            else:  # pragma: no cover - older Tortoise versions
                app_label, model_name = fd.relation.target.rsplit(".", 1)
                rel_model = Tortoise.apps.get(app_label, {}).get(model_name)
            search_fields = getattr(admin, "search_fields", None) or ["name", "title"]
            qs = admin.get_autocomplete_queryset(fd, q, search_fields=search_fields)
            total = await qs.count()
            offset = max(0, (page - 1) * per_page)
            objs = await qs.limit(per_page).offset(offset)
            pk_attr = rel_model._meta.pk_attr
            results = [{"value": getattr(o, pk_attr), "label": str(o)} for o in objs]
            pages = (total + per_page - 1) // per_page
            return {"results": results, "page": page, "pages": pages, "total": total}


__all__ = ["ApiController"]

# The End
