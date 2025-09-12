# -*- coding: utf-8 -*-
"""
site

Core admin site implementation and registration utilities.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List

from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException, Form, status
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from config.settings import settings

from ..adapters import BaseAdapter
from .auth import AdminUserDTO, admin_auth_service
from .permissions import PermAction, permissions_service
from .base import BaseModelAdmin
from .pages import FreeViewPage, SettingsPage
from .settings import SettingsKey, system_config
from .registry import PageRegistry, MenuItem
from .exceptions import AdminModelNotFound
from ..crud import CrudRouterBuilder
from ..api import API_PREFIX, router as api_router
from ..provider import TemplateProvider
from .services import ExportService, ImportService
from .actions import ScopeQueryService, ScopeTokenService
from ..utils.icon import IconPathMixin

Model = Any

logger = logging.getLogger(__name__)



class AdminSite(IconPathMixin):
    """Admin registry: models, pages and menus."""

    def __init__(
        self,
        adapter: BaseAdapter,
        *,
        title: str | None = None,
        templates: Jinja2Templates | None = None,
    ) -> None:
        """Initialize the admin site with required adapter."""
        self.adapter = adapter
        self.AdminContentType = adapter.content_type_model
        self.IntegrityError = getattr(adapter, "IntegrityError", Exception)
        self._title_override = title
        # key: (app_label, model_slug) in lowercase
        self.model_reg: Dict[tuple[str, str], BaseModelAdmin] = {}
        self.registry = PageRegistry()
        self.templates = templates
        # in-process map: (app.lower(), model.lower()) -> ct_id
        self.ct_map: Dict[tuple[str, str], int] = {}
        self._import_service = ImportService()

    @property
    def title(self) -> str:
        """Return configured admin site title."""
        if self._title_override is not None:
            return self._title_override
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

    @staticmethod
    async def _allow(_: Request) -> None:
        return None

    @staticmethod
    def _model_to_slug(name: str) -> str:
        """Return lowercase model name as slug without regex."""
        return name.lower()

    # ==== Registration ====
    def register(
        self,
        app: str,
        model: type[Model],
        admin_cls: type,
        *,
        settings: bool = False,
        icon: str | None = None,
    ) -> None:
        """Register a model admin.

        Args:
            app: application label, e.g. "streams"
            model: ORM model class
            admin_cls: admin class for this model
            settings: register under /settings (True) or /orm (False)
            icon: Bootstrap icon class for menu (e.g. "bi-gear")
        """
        app_label = app
        model_cls = model
        model_slug = self._model_to_slug(model_cls.__name__)

        if admin_cls is None:
            raise ValueError("Admin class is required")

        # Support both admin initializers:
        #   AdminClass(self, app_label, model_slug, adapter)   — new style
        #   AdminClass(model_cls, adapter)                     — old style
        try:
            admin = admin_cls(self, app_label, model_slug, self.adapter)
        except TypeError:
            admin = admin_cls(model_cls, self.adapter)
            setattr(admin, "app_label", app_label)
        display_name = admin.get_verbose_name_plural()

        self.model_reg[(app_label.lower(), model_slug.lower())] = admin
        self.registry.register_view_entry(
            app=app_label,
            model=model_slug,           # store slug in registry
            admin_cls=admin_cls,
            settings=settings,
            icon=icon,
            name=display_name,
        )

    def register_both(
        self,
        app: str,
        model: type[Model],
        admin_cls: type,
        *,
        icon: str | None = None,
    ) -> None:
        """Register the admin in both ORM and Settings modes."""
        self.register(app=app, model=model, admin_cls=admin_cls, settings=False, icon=icon)
        self.register(app=app, model=model, admin_cls=admin_cls, settings=True, icon=icon)

    def all_models(self) -> List[tuple[str, str]]:
        """Return list of registered (app, model) pairs."""
        return list(self.model_reg.keys())

    def find_admin_or_404(self, app: str, model: str) -> BaseModelAdmin:
        """Return admin for given model or raise 404."""
        admin = self.model_reg.get((app.lower(), model.lower()))
        if not admin:
            raise AdminModelNotFound("Unknown admin model")
        return admin

    async def finalize(self) -> None:
        """Idempotent upsert of ContentType records for registered models."""
        for app, model in self.model_reg.keys():
            dotted = f"{app}.{model}"
            ct = await self.adapter.get_or_none(
                self.AdminContentType, dotted=dotted
            )
            if ct is None:
                ct = self.AdminContentType(app_label=app, model=model, dotted=dotted)
                try:
                    await self.adapter.save(ct)
                except self.IntegrityError:
                    ct = await self.adapter.get(
                        self.AdminContentType, dotted=dotted
                    )
            elif (
                ct.app_label != app or ct.model != model or ct.dotted != dotted
            ):
                ct.app_label = app
                ct.model = model
                ct.dotted = dotted
                await self.adapter.save(ct)
            self.ct_map[(app.lower(), model.lower())] = ct.id

    def get_ct_id(self, app: str, model: str) -> int | None:
        """Return ct_id for (app, model) or ``None`` if not registered."""
        return self.ct_map.get((app.lower(), model.lower()))

    def parse_section_path(self, request: Request) -> tuple[bool, str | None, str | None]:
        """Extract section info from ``request.url.path``.

        The returned tuple consists of ``(is_settings, app_label, model_slug)``.
        ``is_settings`` is ``True`` when the path points to the settings section,
        otherwise ``False``. ``app_label`` and ``model_slug`` are extracted from
        ``/orm/<app>/<model>/`` or ``/settings/<app>/<model>/`` URLs. When the
        path does not include app/model parts they are returned as ``None``.
        """

        path = request.url.path
        prefix = system_config.get_cached(
            SettingsKey.ADMIN_PREFIX, settings.ADMIN_PATH
        ).rstrip("/")
        if prefix and path.startswith(prefix):
            path = path[len(prefix) :]

        is_settings = False
        app_label: str | None = None
        model_slug: str | None = None
        base: str | None = None

        settings_prefix = system_config.get_cached(SettingsKey.SETTINGS_PREFIX, "/settings")
        orm_prefix = system_config.get_cached(SettingsKey.ORM_PREFIX, "/orm")

        if path.startswith(settings_prefix + "/") or path == settings_prefix:
            is_settings = True
            base = settings_prefix
        elif path.startswith(orm_prefix + "/") or path == orm_prefix:
            base = orm_prefix

        if base is not None:
            tail = path[len(base) :]
            if tail.startswith("/"):
                tail = tail[1:]
            parts = tail.split("/", 2)
            if len(parts) >= 1 and parts[0]:
                app_label = parts[0]
            if len(parts) >= 2 and parts[1]:
                model_slug = parts[1]

        return is_settings, app_label, model_slug

    @staticmethod
    def _format_app_label(app_label: str) -> str:
        display_label = app_label.replace("_", "\u00A0")
        if display_label:
            display_label = display_label[0].upper() + display_label[1:]
        return display_label

    
    def get_sidebar_apps(self, *, settings: bool) -> List[tuple[str, List[Dict[str, Any]]]]:
        apps: Dict[str, List[Dict[str, Any]]] = {}
        orm_prefix = system_config.get_cached(SettingsKey.ORM_PREFIX, "/orm")
        settings_prefix = system_config.get_cached(SettingsKey.SETTINGS_PREFIX, "/settings")
        for entry in self.registry.view_entries:
            if settings and not entry.settings:
                continue
            if not settings and entry.settings:
                continue
            arr = apps.setdefault(entry.app, [])
            admin = self.model_reg.get((entry.app.lower(), entry.model.lower()))
            display = (
                admin.get_verbose_name_plural()
                if admin is not None
                else entry.name or entry.model.replace("_", " ").title()
            )
            arr.append(
                {
                    "model_name": entry.model,
                    "display_name": display,
                    "path": (settings_prefix if entry.settings else orm_prefix)
                    + f"/{entry.app}/{entry.model}",
                    "icon": entry.icon,
                    "settings": entry.settings,
                }
            )
        out: List[tuple[str, List[Dict[str, Any]]]] = []
        for app_label, models in apps.items():
            models.sort(key=lambda m: m["display_name"].lower())
            out.append((app_label, models))
        out.sort(key=lambda x: x[0].lower())
        return out

    def build_template_ctx(
        self,
        request: Request,
        user: AdminUserDTO | None,
        *,
        page_title: str | None = None,
        app_label: str | None = None,
        model_name: str | None = None,
        is_settings: bool | None = None,
        extra: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Build base template context for admin pages."""
        if is_settings is None or app_label is None or model_name is None:
            parsed_is_settings, parsed_app, parsed_model = self.parse_section_path(request)
            if is_settings is None:
                is_settings = parsed_is_settings
            if app_label is None:
                app_label = parsed_app
            if model_name is None:
                model_name = parsed_model
        raw_apps = self.get_sidebar_apps(settings=is_settings)
        apps = [
            {
                "label": a_label,
                "display": self._format_app_label(a_label),
                "models": models,
            }
            for a_label, models in raw_apps
        ]
        orm_prefix = system_config.get_cached(SettingsKey.ORM_PREFIX, "/orm")
        settings_prefix = system_config.get_cached(SettingsKey.SETTINGS_PREFIX, "/settings")
        views_prefix = system_config.get_cached(SettingsKey.VIEWS_PREFIX, "/views")
        admin_prefix = system_config.get_cached(
            SettingsKey.ADMIN_PREFIX, settings.ADMIN_PATH
        ).rstrip("/")
        ctx: Dict[str, Any] = {
            "request": request,
            "user": user,
            "site_title": self.title,
            "brand_icon": self.brand_icon,
            "prefix": admin_prefix,
            "ORM_PREFIX": orm_prefix,
            "SETTINGS_PREFIX": settings_prefix,
            "VIEWS_PREFIX": views_prefix,
            "apps": apps,
            "current_app": app_label,
            "current_model": model_name,
            "section_mode": "settings" if is_settings else "orm",
            "assets": {"css": [], "js": []},
        }
        if page_title is not None:
            ctx["page_title"] = page_title
        if extra:
            ctx.update(extra)
        return ctx

    def register_view(self, *, path: str, name: str, icon: str | None = None):
        """Register a simple view page handled by ``func``."""

        def decorator(func: Callable[..., Any]):
            page = FreeViewPage(title=name, path=path, icon=icon, handler=func)
            self.registry.page_list.append(page)
            self.registry.menu_list.append(
                MenuItem(title=name, path=path, icon=icon)
            )
            return func
        return decorator

    def register_settings(self, *, path: str, name: str, icon: str | None = None):
        """Register a settings page handled by ``func``."""
        page_type_settings = system_config.get_cached(SettingsKey.PAGE_TYPE_SETTINGS, "settings")

        def decorator(func: Callable[..., Any]):
            page = SettingsPage(title=name, path=path, icon=icon, handler=func)
            self.registry.page_list.append(page)
            self.registry.menu_list.append(
                MenuItem(title=name, path=path, icon=icon, page_type=page_type_settings)
            )
            return func
        return decorator

    def register_user_menu(
        self, *, title: str, path: str, icon: str | None = None
    ) -> None:
        """Register a user menu item."""
        self.registry.register_user_menu_item(title=title, path=path, icon=icon)

    def get_user_menu(self) -> List[Dict[str, str | None]]:
        """Return user menu entries for the current site."""
        return [
            {"label": item.title, "url": item.path, "icon": item.icon}
            for item in self.registry.make_user_menu()
        ]

    # ==== Router ====
    def build_router(self, template_provider: TemplateProvider) -> APIRouter:
        router = APIRouter()
        templates = self.templates or template_provider.get_templates()
        setattr(router, "templates", templates)
        admin_prefix = system_config.get_cached(
            SettingsKey.ADMIN_PREFIX, settings.ADMIN_PATH
        ).rstrip("/")

        def get_admin_api() -> dict[str, str]:
            """Expose fully-qualified API paths for templates."""

            api_prefix = system_config.get_cached(SettingsKey.API_PREFIX, "/api")
            schema_rel = system_config.get_cached(SettingsKey.API_SCHEMA, "/schema")
            list_filters_rel = system_config.get_cached(
                SettingsKey.API_LIST_FILTERS, "/list_filters"
            )
            base = admin_prefix

            return {
                "prefix": f"{base}{api_prefix}",
                "schema": f"{base}{api_prefix}{schema_rel}",
                "list_filters": f"{base}{api_prefix}{list_filters_rel}",
            }

        templates.env.globals.update(
            iter_settings_entries=self.registry.iter_settings,
            iter_orm_entries=self.registry.iter_orm,
            get_admin_api=get_admin_api,
            get_user_menu=self.get_user_menu,
        )

        orm_prefix = system_config.get_cached(SettingsKey.ORM_PREFIX, "/orm")
        settings_prefix = system_config.get_cached(SettingsKey.SETTINGS_PREFIX, "/settings")
        views_prefix = system_config.get_cached(SettingsKey.VIEWS_PREFIX, "/views")
        page_type_settings = system_config.get_cached(SettingsKey.PAGE_TYPE_SETTINGS)

        self._attach_auth_routes(router, templates)
        self._attach_page_routes(
            router,
            templates,
            orm_prefix,
            settings_prefix,
            views_prefix,
            page_type_settings,
            admin_prefix,
        )
        self._attach_api_routes(router)
        self._attach_crud_routes(router, orm_prefix, settings_prefix)

        return router

    def _attach_auth_routes(
        self, router: APIRouter, templates: Jinja2Templates
    ) -> None:
        logout_path = system_config.get_cached(SettingsKey.LOGOUT_PATH, "/logout")
        self.register_user_menu(title="Logout", path=logout_path)
        router.include_router(
            admin_auth_service.build_auth_router(templates), tags=["admin-auth"]
        )

    def _attach_page_routes(
        self,
        router: APIRouter,
        templates: Jinja2Templates,
        orm_prefix: str,
        settings_prefix: str,
        views_prefix: str,
        page_type_settings: str,
        admin_prefix: str,
    ) -> None:
        @router.get("/", response_class=HTMLResponse)
        async def admin_index(
            request: Request,
            user: AdminUserDTO = Depends(
                admin_auth_service.require_permissions((), admin_site=self)
            ),
        ) -> HTMLResponse:
            dash_title = await system_config.get(SettingsKey.DASHBOARD_PAGE_TITLE)
            return templates.TemplateResponse(
                "pages/index.html",
                {
                    "request": request,
                    "site_title": self.title,
                    "user": user,
                    "brand_icon": self.brand_icon,
                    "page_title": dash_title,
                    "prefix": admin_prefix,
                    "ORM_PREFIX": orm_prefix,
                    "SETTINGS_PREFIX": settings_prefix,
                    "VIEWS_PREFIX": views_prefix,
                },
            )

        for page in [p for p in self.registry.page_list if isinstance(p, FreeViewPage)]:
            user_dep = (
                admin_auth_service.get_current_admin_user
                if page.page_type == page_type_settings
                else admin_auth_service.require_permissions((), admin_site=self)
            )
            perm_dep = (
                permissions_service.require_global_permission(PermAction.view)
                if page.page_type == page_type_settings
                else self._allow
            )

            async def view_handler(
                request: Request,
                page: FreeViewPage = Depends(lambda page=page: page),
                user: AdminUserDTO = Depends(user_dep),
                _ = Depends(perm_dep),
            ) -> HTMLResponse:
                ctx: Dict[str, Any] = {}
                if page.handler:
                    res = page.handler(request=request, user=user)
                    if hasattr(res, "__await__"):
                        res = await res  # type: ignore
                    ctx = res or {}
                is_settings = (
                    page.page_type == page_type_settings
                    or page.path == settings_prefix
                )
                if page.path == orm_prefix:
                    template_name = "pages/orm.html"
                elif page.path == settings_prefix:
                    template_name = "pages/settings.html"
                elif page.path == views_prefix:
                    template_name = "pages/views.html"
                else:
                    template_name = "layout/default.html"
                base_ctx = self.build_template_ctx(
                    request,
                    user,
                    page_title=page.title,
                    is_settings=is_settings,
                    extra=ctx,
                )
                if page.path != views_prefix:
                    base_ctx["menu"] = self.registry.make_menu()
                return templates.TemplateResponse(template_name, base_ctx)

            router.add_api_route(
                page.path, view_handler, methods=["GET"], name=page.title
            )

    def _attach_api_routes(self, router: APIRouter) -> None:
        router.include_router(api_router, prefix=API_PREFIX)

    def _attach_crud_routes(
        self, router: APIRouter, orm_prefix: str, settings_prefix: str
    ) -> None:
        templates = getattr(router, "templates", None)
        if templates is None:
            base_dir = Path(__file__).resolve().parents[2]
            templates = Jinja2Templates(directory=str(base_dir / "templates"))
        for entry in self.registry.iter_orm():
            app_label = entry.app
            model_slug = entry.model
            prefix = f"{orm_prefix}/{app_label}/{model_slug}"
            CrudRouterBuilder.mount(
                router,
                admin_site=self,
                prefix=prefix,
                admin_cls=entry.admin_cls,
                perms="model",
                app_label=app_label,
            )
            admin = self.model_reg.get((app_label.lower(), model_slug.lower()))
            if admin is None:
                continue
            export_endpoint_name = f"{app_label}_{model_slug}_export_wizard"
            export_preview_endpoint_name = f"{app_label}_{model_slug}_export_preview"
            export_run_endpoint_name = f"{app_label}_{model_slug}_export_run"
            export_done_endpoint_name = f"{app_label}_{model_slug}_export_done"
            admin.export_endpoint_name = export_endpoint_name
            admin.export_preview_endpoint_name = export_preview_endpoint_name
            admin.export_run_endpoint_name = export_run_endpoint_name
            admin.export_done_endpoint_name = export_done_endpoint_name
            export_service = ExportService(self.adapter)
            scope_query_service = ScopeQueryService(self.adapter)
            scope_token_service = ScopeTokenService()
            scope_token_service = ScopeTokenService()
            if admin.perm_export:
                perm_export = permissions_service.require_model_permission(
                    admin.perm_export, app_value=app_label, model_value=model_slug
                )
            else:
                async def perm_export(request: Request) -> None:
                    return None
            if admin.perm_import:
                perm_import = permissions_service.require_model_permission(
                    admin.perm_import, app_value=app_label, model_value=model_slug
                )
            else:
                async def perm_import(request: Request) -> None:
                    return None

            @router.api_route(
                prefix + "/export/",
                methods=["GET", "POST"],
                response_class=HTMLResponse,
                name=export_endpoint_name,
            )
            async def export_step1(
                request: Request,
                user: AdminUserDTO = Depends(
                    admin_auth_service.get_current_admin_user
                ),
                _=Depends(perm_export),
                admin=admin,
                app_label: str = app_label,
                model_slug: str = model_slug,
            ) -> HTMLResponse:
                request.state.user_dto = user
                if not (user.is_superuser or admin.has_export_perm(request)):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Export not permitted",
                    )
                ctx = self.build_template_ctx(
                    request,
                    user,
                    page_title="Export",
                    app_label=app_label,
                    model_name=model_slug,
                )
                ctx["fields"] = list(admin.get_export_fields())
                return templates.TemplateResponse(
                    "context/export.html", ctx
                )

            @router.post(prefix + "/export/preview", name=export_preview_endpoint_name)
            async def export_preview(
                request: Request,
                user: AdminUserDTO = Depends(
                    admin_auth_service.get_current_admin_user
                ),
                _=Depends(perm_export),
                admin=admin,
                export_service: ExportService = Depends(lambda: export_service),
                scope_query_service: ScopeQueryService = Depends(
                    lambda: scope_query_service
                ),
            ) -> Dict[str, Any]:
                request.state.user_dto = user
                if not (user.is_superuser or admin.has_export_perm(request)):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Export not permitted",
                    )
                payload = await request.json()
                allowed = list(admin.get_export_fields())
                fields = [f for f in payload.get("fields", allowed) if f in allowed]
                md = self.adapter.get_model_descriptor(admin.model)
                scope = payload.get("scope")
                if scope is None:
                    token = payload.get("scope_token")
                    if token is None:
                        raise HTTPException(status_code=400, detail="Missing scope")
                    try:
                        scope = scope_token_service.verify(token)
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Invalid scope_token")
                qs = scope_query_service.build_queryset(
                    admin, md, request, user, scope
                )
                rows = await export_service.preview(qs, fields)
                return {"count": len(rows), "rows": rows}

            @router.post(prefix + "/export/run", name=export_run_endpoint_name)
            async def export_run(
                request: Request,
                user: AdminUserDTO = Depends(
                    admin_auth_service.get_current_admin_user
                ),
                _=Depends(perm_export),
                admin=admin,
                export_service: ExportService = Depends(lambda: export_service),
                scope_query_service: ScopeQueryService = Depends(
                    lambda: scope_query_service
                ),
            ) -> Dict[str, Any]:
                request.state.user_dto = user
                if not (user.is_superuser or admin.has_export_perm(request)):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Export not permitted",
                    )
                payload = await request.json()
                allowed = list(admin.get_export_fields())
                fields = [f for f in payload.get("fields", allowed) if f in allowed]
                fmt = payload.get("fmt", "json")
                md = self.adapter.get_model_descriptor(admin.model)
                scope = payload.get("scope")
                if scope is None:
                    token = payload.get("scope_token")
                    if token is None:
                        raise HTTPException(status_code=400, detail="Missing scope")
                    try:
                        scope = scope_token_service.verify(token)
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Invalid scope_token")
                qs = scope_query_service.build_queryset(
                    admin, md, request, user, scope
                )
                token = await export_service.run(
                    qs, fields, fmt, model_name=admin.model.__name__
                )
                return {"token": token}

            @router.get(prefix + "/export/done/{token}", name=export_done_endpoint_name)
            async def export_done(
                token: str,
                request: Request,
                user: AdminUserDTO = Depends(
                    admin_auth_service.get_current_admin_user
                ),
                _=Depends(perm_export),
                admin=admin,
                export_service: ExportService = Depends(lambda: export_service),
            ) -> StreamingResponse:
                request.state.user_dto = user
                if not (user.is_superuser or admin.has_export_perm(request)):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Export not permitted",
                    )
                cached = export_service.get_file(token)
                def iterfile() -> Any:
                    with cached.path.open("rb") as f:
                        yield from f
                response = StreamingResponse(iterfile(), media_type=cached.mime)
                response.headers[
                    "Content-Disposition"
                ] = f"attachment; filename={cached.filename}"
                response.headers["Content-Type"] = cached.mime
                return response

            import_endpoint_name = f"{app_label}_{model_slug}_import_wizard"
            import_preview_name = f"{app_label}_{model_slug}_import_preview"
            import_run_name = f"{app_label}_{model_slug}_import_run"
            admin.import_endpoint_name = import_endpoint_name
            admin.import_preview_endpoint_name = import_preview_name
            admin.import_run_endpoint_name = import_run_name

            @router.api_route(
                prefix + "/import/",
                methods=["GET", "POST"],
                response_class=HTMLResponse,
                name=import_endpoint_name,
            )
            async def import_step1(
                request: Request,
                user: AdminUserDTO = Depends(
                    admin_auth_service.get_current_admin_user
                ),
                _=Depends(perm_import),
                admin=admin,
                app_label: str = app_label,
                model_slug: str = model_slug,
            ) -> HTMLResponse:
                request.state.user_dto = user
                if not admin.has_import_perm(request):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Import not permitted",
                    )
                ctx = self.build_template_ctx(
                    request,
                    user,
                    page_title="Import",
                    app_label=app_label,
                    model_name=model_slug,
                )
                ctx.update(
                    fields=list(admin.get_import_fields()),
                    required=set(admin.get_required_import_fields()),
                )
                return templates.TemplateResponse(
                    "context/import.html", ctx
                )

            @router.post(prefix + "/import/preview", name=import_preview_name)
            async def import_preview(
                request: Request,
                file: UploadFile = File(...),
                fields: list[str] = Form(...),
                user: AdminUserDTO = Depends(
                    admin_auth_service.get_current_admin_user
                ),
                _=Depends(perm_import),
                admin=admin,
                import_service: ImportService = Depends(
                    lambda: self._import_service
                ),
            ) -> Dict[str, Any]:
                request.state.user_dto = user
                if not admin.has_import_perm(request):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Import not permitted",
                    )
                token = await import_service.cache_upload(file)
                rows = await import_service.preview(token, fields)
                return {"token": token, "rows": rows}

            @router.post(prefix + "/import/run", name=import_run_name)
            async def import_run(
                request: Request,
                user: AdminUserDTO = Depends(
                    admin_auth_service.get_current_admin_user
                ),
                _=Depends(perm_import),
                admin=admin,
                import_service: ImportService = Depends(
                    lambda: self._import_service
                ),
            ) -> Dict[str, Any]:
                request.state.user_dto = user
                if not admin.has_import_perm(request):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Import not permitted",
                    )
                payload = await request.json()
                token = payload.get("token")
                dry = payload.get("dry", False)
                fields = payload.get("fields") or list(admin.get_import_fields())
                report = await import_service.run(admin, token, fields, dry=dry)
                import_service.cleanup(token)
                return report.__dict__

        for entry in self.registry.iter_settings():
            app_label = entry.app
            model_slug = entry.model
            prefix = f"{settings_prefix}/{app_label}/{model_slug}"
            CrudRouterBuilder.mount(
                router,
                admin_site=self,
                prefix=prefix,
                admin_cls=entry.admin_cls,
                perms="global",
                app_label=app_label,
            )
            admin = self.model_reg.get((app_label.lower(), model_slug.lower()))
            if admin is None:
                continue
            export_endpoint_name = f"{app_label}_{model_slug}_export_wizard"
            export_preview_endpoint_name = f"{app_label}_{model_slug}_export_preview"
            export_run_endpoint_name = f"{app_label}_{model_slug}_export_run"
            export_done_endpoint_name = f"{app_label}_{model_slug}_export_done"
            admin.export_endpoint_name = export_endpoint_name
            admin.export_preview_endpoint_name = export_preview_endpoint_name
            admin.export_run_endpoint_name = export_run_endpoint_name
            admin.export_done_endpoint_name = export_done_endpoint_name
            export_service = ExportService(self.adapter)
            scope_query_service = ScopeQueryService(self.adapter)
            if admin.perm_export:
                perm_export = permissions_service.require_global_permission(
                    admin.perm_export
                )
            else:
                async def perm_export(request: Request) -> None:
                    return None

            @router.api_route(
                prefix + "/export/",
                methods=["GET", "POST"],
                response_class=HTMLResponse,
                name=export_endpoint_name,
            )
            async def export_step1(
                request: Request,
                user: AdminUserDTO = Depends(
                    admin_auth_service.get_current_admin_user
                ),
                _=Depends(perm_export),
                admin=admin,
                app_label: str = app_label,
                model_slug: str = model_slug,
            ) -> HTMLResponse:
                request.state.user_dto = user
                if not (user.is_superuser or admin.has_export_perm(request)):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Export not permitted",
                    )
                ctx = self.build_template_ctx(
                    request,
                    user,
                    page_title="Export",
                    app_label=app_label,
                    model_name=model_slug,
                )
                ctx["fields"] = list(admin.get_export_fields())
                return templates.TemplateResponse(
                    "context/export.html", ctx
                )

            @router.post(prefix + "/export/preview", name=export_preview_endpoint_name)
            async def export_preview(
                request: Request,
                user: AdminUserDTO = Depends(
                    admin_auth_service.get_current_admin_user
                ),
                _=Depends(perm_export),
                admin=admin,
                export_service: ExportService = Depends(lambda: export_service),
                scope_query_service: ScopeQueryService = Depends(
                    lambda: scope_query_service
                ),
            ) -> Dict[str, Any]:
                request.state.user_dto = user
                if not (user.is_superuser or admin.has_export_perm(request)):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Export not permitted",
                    )
                payload = await request.json()
                allowed = list(admin.get_export_fields())
                fields = [f for f in payload.get("fields", allowed) if f in allowed]
                md = self.adapter.get_model_descriptor(admin.model)
                scope = payload.get("scope")
                if scope is None:
                    token = payload.get("scope_token")
                    if token is None:
                        raise HTTPException(status_code=400, detail="Missing scope")
                    try:
                        scope = scope_token_service.verify(token)
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Invalid scope_token")
                qs = scope_query_service.build_queryset(
                    admin, md, request, user, scope
                )
                rows = await export_service.preview(qs, fields)
                return {"count": len(rows), "rows": rows}

            @router.post(prefix + "/export/run", name=export_run_endpoint_name)
            async def export_run(
                request: Request,
                user: AdminUserDTO = Depends(
                    admin_auth_service.get_current_admin_user
                ),
                _=Depends(perm_export),
                admin=admin,
                export_service: ExportService = Depends(lambda: export_service),
                scope_query_service: ScopeQueryService = Depends(
                    lambda: scope_query_service
                ),
            ) -> Dict[str, Any]:
                request.state.user_dto = user
                if not (user.is_superuser or admin.has_export_perm(request)):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Export not permitted",
                    )
                payload = await request.json()
                allowed = list(admin.get_export_fields())
                fields = [f for f in payload.get("fields", allowed) if f in allowed]
                fmt = payload.get("fmt", "json")
                md = self.adapter.get_model_descriptor(admin.model)
                scope = payload.get("scope")
                if scope is None:
                    token = payload.get("scope_token")
                    if token is None:
                        raise HTTPException(status_code=400, detail="Missing scope")
                    try:
                        scope = scope_token_service.verify(token)
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Invalid scope_token")
                qs = scope_query_service.build_queryset(
                    admin, md, request, user, scope
                )
                token = await export_service.run(
                    qs, fields, fmt, model_name=admin.model.__name__
                )
                return {"token": token}

            @router.get(prefix + "/export/done/{token}", name=export_done_endpoint_name)
            async def export_done(
                token: str,
                request: Request,
                user: AdminUserDTO = Depends(
                    admin_auth_service.get_current_admin_user
                ),
                _=Depends(perm_export),
                admin=admin,
                export_service: ExportService = Depends(lambda: export_service),
            ) -> StreamingResponse:
                request.state.user_dto = user
                if not (user.is_superuser or admin.has_export_perm(request)):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Export not permitted",
                    )
                cached = export_service.get_file(token)

                def iterfile() -> Any:
                    with cached.path.open("rb") as f:
                        yield from f

                response = StreamingResponse(iterfile(), media_type=cached.mime)
                response.headers[
                    "Content-Disposition"
                ] = f"attachment; filename={cached.filename}"
                response.headers["Content-Type"] = cached.mime
                return response

        self.registry.make_menu()

# The End

