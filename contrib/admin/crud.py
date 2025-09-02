# -*- coding: utf-8 -*-
"""
crud

Utility for mounting CRUD routes on FastAPI routers.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable, Literal, TYPE_CHECKING

from fastapi import APIRouter, Body, Depends, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config.settings import settings
from .core.auth import AdminUserDTO, admin_auth_service
from .core.base import BaseModelAdmin
from .core.permissions import PermAction, permissions_service
from .core.services import AdminService
from .core.exceptions import HTTPError
from .core.settings import SettingsKey, system_config


if TYPE_CHECKING:
    from .core.site import AdminSite


class CrudRouterBuilder:
    """Helper to attach standard CRUD routes for admin classes."""

    @staticmethod
    def mount(
        router: APIRouter,
        *,
        admin_site: AdminSite,
        prefix: str,
        admin_cls: type[BaseModelAdmin],
        perms: Literal["model", "global"],
        app_label: str,
        model_name: str,
    ) -> APIRouter:
        """Mount standard CRUD routes for ``admin_cls`` on ``router``.

        ``prefix`` is the base path. ``perms`` controls whether permissions are
        checked against a specific model (``"model"``) or globally
        (``"global"``).
        """

        templates = getattr(router, "templates", None)
        if templates is None:
            base_dir = Path(__file__).resolve().parents[2]
            templates = Jinja2Templates(directory=str(base_dir / "templates"))

        adapter = getattr(admin_site, "adapter", None)
        if adapter is None:
            from .boot import admin as boot_admin  # pragma: no cover
            adapter = boot_admin.adapter
        admin = admin_cls(admin_cls.model, adapter)
        setattr(admin, "app_label", app_label)
        setattr(admin, "model_slug", model_name)
        service = AdminService(admin)
        md = service.md

        perm_view: Callable[[Request], Awaitable[Any]]
        perm_add: Callable[[Request], Awaitable[Any]]
        perm_change: Callable[[Request], Awaitable[Any]]
        perm_delete: Callable[[Request], Awaitable[Any]]
        if perms == "global":
            perm_view = permissions_service.require_global_permission(PermAction.view)
            perm_add = permissions_service.require_global_permission(PermAction.add)
            perm_change = permissions_service.require_global_permission(
                PermAction.change
            )
            perm_delete = permissions_service.require_global_permission(
                PermAction.delete
            )
        else:
            perm_view = permissions_service.require_model_permission(
                PermAction.view, app_value=app_label, model_value=model_name
            )
            perm_add = permissions_service.require_model_permission(
                PermAction.add, app_value=app_label, model_value=model_name
            )
            perm_change = permissions_service.require_model_permission(
                PermAction.change, app_value=app_label, model_value=model_name
            )
            perm_delete = permissions_service.require_model_permission(
                PermAction.delete, app_value=app_label, model_value=model_name
            )

        # model descriptor already provided by the service

        @router.get(prefix + "/", response_class=HTMLResponse)
        async def list_page(
            request: Request,
            user: AdminUserDTO = Depends(
                admin_auth_service.get_current_admin_user
            ),
            _ = Depends(perm_view),
        ) -> HTMLResponse:
            can_add = admin.allow(user, "add")
            ctx = admin_site.build_template_ctx(
                request,
                user,
                app_label=app_label,
                model_name=model_name,
                is_settings=(perms == "global"),
                extra={
                    "can_add": can_add,
                    "has_list_filters": bool(admin.get_list_filter()),
                    "has_search": bool(admin.get_search_fields(md)),
                },
            )
            return templates.TemplateResponse("context/list.html", ctx)

        @router.get(prefix + "/add", response_class=HTMLResponse)
        async def add_page(
            request: Request,
            user: AdminUserDTO = Depends(
                admin_auth_service.get_current_admin_user
            ),
            _ = Depends(perm_add),
        ) -> HTMLResponse:
            title = f"Add {admin.get_verbose_name()}"
            ctx = admin_site.build_template_ctx(
                request,
                user,
                page_title=title,
                app_label=app_label,
                model_name=model_name,
                is_settings=(perms == "global"),
            )
            md = admin.adapter.get_model_descriptor(admin.model)
            assets = admin.collect_assets(md, mode="add", obj=None, request=request)
            ctx["assets"] = assets
            return templates.TemplateResponse("context/form.html", ctx)

        @router.get(prefix + "/{pk}/edit", response_class=HTMLResponse)
        async def edit_page(
            request: Request,
            pk: str,
            user: AdminUserDTO = Depends(
                admin_auth_service.get_current_admin_user
            ),
            _ = Depends(perm_change),
        ) -> HTMLResponse:
            try:
                obj = await service.get_object(request, user, pk)
            except HTTPError as exc:
                raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
            title = f"Edit {admin.get_verbose_name()}"
            ctx = admin_site.build_template_ctx(
                request,
                user,
                page_title=title,
                app_label=app_label,
                model_name=model_name,
                is_settings=(perms == "global"),
                extra={"pk": pk},
            )
            md = admin.adapter.get_model_descriptor(admin.model)
            assets = admin.collect_assets(md, mode="edit", obj=obj, request=request)
            ctx["assets"] = assets
            return templates.TemplateResponse("context/form.html", ctx)

        # form schema served via global API; no local endpoint

        @router.get(prefix + "/_list")
        async def list_data(
            request: Request,
            search: str = "",
            page_num: int = 1,
            per_page: int | None = None,
            order: str = "",
            user: AdminUserDTO = Depends(
                admin_auth_service.get_current_admin_user
            ),
            _ = Depends(perm_view),
        ):
            try:
                return await service.list_data(
                    request, user, search, page_num, per_page, order
                )
            except HTTPError as exc:
                raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

        @router.get(prefix + "/_actions")
        async def action_specs(
            request: Request,
            user: AdminUserDTO = Depends(
                admin_auth_service.get_current_admin_user
            ),
            _ = Depends(perm_view),
        ):
            return admin.get_action_specs(user)

        @router.post(prefix + "/_actions/{name}")
        async def run_action(
            request: Request,
            name: str,
            payload: dict = Body(...),
            user: AdminUserDTO = Depends(
                admin_auth_service.get_current_admin_user
            ),
            _ = Depends(perm_view),
        ):
            try:
                return await service.run_action(
                    request, user, name, payload, app_label, model_name
                )
            except HTTPError as exc:
                raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

        async def _perm_upload(request: Request) -> None:
            try:
                await perm_add(request)
            except HTTPException:
                await perm_change(request)

        @router.post(prefix + "/upload")
        async def upload(
            request: Request,
            file: UploadFile = File(...),
            user: AdminUserDTO = Depends(
                admin_auth_service.get_current_admin_user
            ),
            _ = Depends(_perm_upload),
        ):
            media_root = Path(
                system_config.get_cached(SettingsKey.MEDIA_ROOT, settings.MEDIA_ROOT)
            )
            rel_dir = Path(app_label) / model_name
            target = media_root / rel_dir
            target.mkdir(parents=True, exist_ok=True)
            filename = Path(file.filename or "upload").name
            dest = target / filename
            stem = dest.stem
            suffix = dest.suffix
            idx = 1
            while dest.exists():
                dest = target / f"{stem}-{idx}{suffix}"
                idx += 1
            data = await file.read()
            with open(dest, "wb") as fh:
                fh.write(data)
            await file.close()
            rel_path = rel_dir / dest.name
            return {"url": str(rel_path).replace("\\", "/")}

        @router.post(prefix)
        async def create(
            request: Request,
            payload: dict = Body(...),
            user: AdminUserDTO = Depends(
                admin_auth_service.get_current_admin_user
            ),
            _ = Depends(perm_add),
        ):
            try:
                return await service.create(request, user, payload)
            except HTTPError as exc:
                raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

        @router.put(prefix + "/{pk}")
        async def update(
            request: Request,
            pk: str,
            payload: dict = Body(...),
            user: AdminUserDTO = Depends(
                admin_auth_service.get_current_admin_user
            ),
            _ = Depends(perm_change),
        ):
            try:
                return await service.update(request, user, pk, payload)
            except HTTPError as exc:
                raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

        @router.delete(prefix + "/{pk}")
        async def delete(
            request: Request,
            pk: str,
            user: AdminUserDTO = Depends(
                admin_auth_service.get_current_admin_user
            ),
            _ = Depends(perm_delete),
        ):
            try:
                return await service.delete(request, user, pk)
            except HTTPError as exc:
                raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

        return router

# The End

