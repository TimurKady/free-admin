# -*- coding: utf-8 -*-
"""
Dataclasses describing different kinds of admin pages.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
    TYPE_CHECKING,
)

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from .settings import SettingsKey, system_config
from .auth import admin_auth_service
from .services.permissions import PermAction
from .templates import TemplateRenderer, TemplateService

if TYPE_CHECKING:  # pragma: no cover - typing helpers only
    from .site import AdminSite


class BaseTemplatePage:
    """Provide reusable registration helpers for admin and public pages.

    Subclass this helper when you need class-based pages that automatically
    integrate with :class:`AdminSite`. Declare the route metadata (``path``,
    ``name``, optional ``icon`` and ``label``), point ``template`` at the
    template to render, and optionally supply ``template_directory`` so the
    renderer can discover project-specific templates. Instantiating the
    subclass wires the template directories into the shared
    :class:`TemplateService` and keeps registrations idempotent.

    Override :meth:`get_context` to provide extra values for the template. When
    you call :meth:`register_admin_view` or :meth:`register_public_view`, the
    class wraps :meth:`get_context` in an async handler compatible with
    FastAPI's routing layer. You can still override :meth:`get_handler` (or
    :meth:`get_public_handler`) when you need complete control over the
    endpoint implementation.
    """

    path: str
    name: str
    template: str | None = None
    template_directory: str | Path | Iterable[str | Path] | None = None
    icon: str | None = None
    label: str | None = None
    settings: bool | None = None
    include_in_sidebar: bool = True

    def __init__(
        self,
        *,
        site: "AdminSite",
        template_service: TemplateService | None = None,
    ) -> None:
        """Store dependencies and register template directories with the service."""

        self._site = site
        self._template_service = template_service or TemplateRenderer.get_service()
        self._admin_handler: Callable[..., Any] | None = None
        self._public_handler: Callable[..., Any] | None = None
        self._register_template_directories()
        self._template_service.ensure_site_templates(self._site)

    @property
    def admin_handler(self) -> Callable[..., Any] | None:
        """Return the registered administrative handler, if available."""

        return self._admin_handler

    @property
    def public_handler(self) -> Callable[..., Any] | None:
        """Return the registered public handler, if available."""

        return self._public_handler

    def register_admin_view(self) -> None:
        """Register the page as an administrative view on the configured site."""

        if self._admin_handler is not None:
            return
        handler = self.get_handler()
        if handler is None:
            handler = self._build_admin_context_handler()
        decorator = self._site.register_view(
            path=self.path,
            name=self.name,
            icon=self.icon,
            label=self.label,
            settings=self.settings,
            include_in_sidebar=self.include_in_sidebar,
        )
        self._admin_handler = decorator(handler)

    def register_public_view(self) -> None:
        """Register the page as a public view rendered through templates."""

        if self.template is None:
            raise ValueError("Public pages require a template name.")
        if self._public_handler is not None:
            return
        handler = self.get_public_handler()
        if handler is None:
            handler = self._build_public_context_handler()
        decorator = self._site.register_public_view(
            path=self.path,
            name=self.name,
            template=self.template,
            icon=self.icon,
        )
        self._public_handler = decorator(handler)

    def get_handler(self) -> Callable[..., Any] | None:
        """Return a custom handler for administrative registration when needed."""

        return None

    def get_public_handler(self) -> Callable[..., Any] | None:
        """Return a custom handler for public registration when needed."""

        return self.get_handler()

    async def get_context(
        self,
        *,
        request: Request,
        user: object | None = None,
    ) -> Mapping[str, Any]:
        """Return extra context injected into template rendering."""

        return {}

    def _build_admin_context_handler(self) -> Callable[..., Awaitable[Mapping[str, Any]]]:
        """Wrap :meth:`get_context` for administrative routing."""

        async def handler(request: Request, user: object) -> Mapping[str, Any]:
            return await self._resolve_context(request=request, user=user)

        return handler

    def _build_public_context_handler(self) -> Callable[..., Awaitable[Mapping[str, Any]]]:
        """Wrap :meth:`get_context` for public routing with optional user."""

        async def handler(
            request: Request,
            user: object | None = None,
        ) -> Mapping[str, Any]:
            return await self._resolve_context(request=request, user=user)

        return handler

    async def _resolve_context(
        self,
        *,
        request: Request,
        user: object | None,
    ) -> Mapping[str, Any]:
        """Resolve context values returned by :meth:`get_context`."""

        result = self.get_context(request=request, user=user)
        if hasattr(result, "__await__"):
            result = await result  # type: ignore[assignment]
        if result is None:
            return {}
        if not isinstance(result, Mapping):
            raise TypeError(
                "get_context must return a mapping-compatible object"
            )
        return dict(result)

    def _register_template_directories(self) -> None:
        """Add declared template directories to the shared service."""

        directory = self.template_directory
        if directory is None:
            return
        directories: Iterable[str | Path]
        if isinstance(directory, (str, Path)):
            directories = (directory,)
        else:
            directories = directory
        for item in directories:
            self._template_service.add_template_directory(item)


@dataclass(frozen=True)
class AdminPage:
    """Common fields shared by all pages in the admin interface."""

    title: str
    path: str
    icon: str | None = field(default=None, kw_only=True)
    page_type: str = field(
        default_factory=lambda: system_config.get_cached(
            SettingsKey.PAGE_TYPE_VIEW, "view"
        ),
        kw_only=True,
    )


@dataclass(frozen=True)
class FreeViewPage(AdminPage):
    """Arbitrary view rendered via a supplied handler."""

    # async/sync callable(request, user) -> dict
    handler: Callable[..., Any] | None = None
    app_label: str | None = field(default=None, kw_only=True)
    app_slug: str | None = field(default=None, kw_only=True)
    slug: str | None = field(default=None, kw_only=True)
    dotted: str | None = field(default=None, kw_only=True)


@dataclass(frozen=True)
class ModelPage(AdminPage):
    """Page representing an ORM model."""

    singular_title: str
    app_label: str
    model_name: str
    dotted: str
    # path for the model section will be of the form: /orm/{app}/{model}/


@dataclass(frozen=True)
class SettingsPage(FreeViewPage):
    """Administrative page for application settings."""

    page_type: str = field(
        default_factory=lambda: system_config.get_cached(
            SettingsKey.PAGE_TYPE_SETTINGS, "settings"
        )
    )


@dataclass
class PageResolution:
    """Describe how a URL path maps onto the admin navigation tree."""

    normalized_path: str
    section_mode: str
    is_settings: bool
    app_label: str | None
    model_slug: str | None
    descriptor: "PageDescriptor | None"


@dataclass
class PageDescriptor:
    """Store metadata for registered admin, settings, or public pages."""

    manager: "PageDescriptorManager"
    title: str
    path: str
    icon: str | None
    normalized_path: str
    normalized_key: str
    owning_label: str
    section: str
    include_in_sidebar: bool
    has_required_tail: bool
    settings: bool
    model_name: str
    app_label: str | None
    app_slug: str | None
    slug: str | None
    dotted: str | None
    page_class: type[AdminPage]
    menu_page_type: str | None = None
    template_name: str | None = None
    public: bool = False
    handler: Callable[..., Any] | None = None
    page: AdminPage | None = None

    def bind_handler(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Attach ``func`` as the handler for the registered page."""

        self.handler = func
        site = self.manager.admin_site
        if issubclass(self.page_class, FreeViewPage):
            page_kwargs = {
                "title": self.title,
                "path": self.normalized_path,
                "icon": self.icon,
                "handler": func,
                "app_label": self.app_label,
                "app_slug": self.app_slug,
                "slug": self.slug,
                "dotted": self.dotted,
            }
            self.page = self.page_class(**page_kwargs)  # type: ignore[arg-type]
            site.registry.register_page(self.page)
            site.menu_builder.register_item(
                title=self.title,
                path=self.normalized_path,
                icon=self.icon,
                page_type=self.menu_page_type,
            )
            site.menu_builder.invalidate_main_menu()
        return func

    def build_sidebar_entry(self) -> Dict[str, Any]:
        """Return sidebar entry payload for the descriptor."""

        return {
            "model_name": self.model_name,
            "display_name": self.title,
            "path": self.normalized_path,
            "icon": self.icon,
            "settings": self.settings,
        }

    def mount_admin_route(
        self,
        router: APIRouter,
        *,
        templates,
        page_type_settings: str,
        views_prefix: str,
        settings_prefix: str,
        orm_prefix: str,
    ) -> None:
        """Attach the descriptor as a GET route under the admin router."""

        page = self.page
        if not isinstance(page, FreeViewPage):
            return
        site = self.manager.admin_site
        user_dependency = (
            admin_auth_service.get_current_admin_user
            if page.page_type == page_type_settings
            else admin_auth_service.require_permissions((), admin_site=site)
        )
        registry_virtual = site.registry.get_view_virtual_by_path(page.path)
        dotted_key = page.dotted or (registry_virtual.dotted if registry_virtual else None)
        perm_dep = site.permission_checker.require_view(
            PermAction.view,
            dotted=dotted_key,
            view_key=page.path if dotted_key is None else None,
            admin_site=site,
        )

        async def endpoint(
            request: Request,
            page: FreeViewPage = Depends(lambda page=page: page),
            user=Depends(user_dependency),
            _perm=Depends(perm_dep),
        ) -> HTMLResponse:
            ctx: Dict[str, Any] = {}
            if page.handler:
                result = page.handler(request=request, user=user)
                if hasattr(result, "__await__"):
                    result = await result  # type: ignore[func-returns-value]
                if isinstance(result, Mapping):
                    ctx = dict(result)
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
                template_name = "layout/section.html"
            base_ctx = site.build_template_ctx(
                request,
                user,
                page_title=page.title,
                is_settings=is_settings,
                extra=ctx,
            )
            if page.path != views_prefix:
                base_ctx["menu"] = site.menu_builder.build_main_menu(
                    locale=site.get_locale(request)
                )
            return templates.TemplateResponse(template_name, base_ctx)

        router.add_api_route(
            page.path, endpoint, methods=["GET"], name=page.title
        )

    def mount_public_route(self, router: APIRouter) -> None:
        """Attach the descriptor as an anonymous page under ``router``."""

        if not self.public or not self.template_name:
            return
        responder = self.manager.page_responder

        async def endpoint(request: Request) -> HTMLResponse:
            context: Dict[str, Any] = {}
            if self.handler is not None:
                result = self.handler(request=request, user=None)
                if hasattr(result, "__await__"):
                    result = await result  # type: ignore[func-returns-value]
                if isinstance(result, Mapping):
                    context = dict(result)
            return responder.render(
                self.template_name,
                request=request,
                context=context,
                title=self.title,
            )

        router.add_api_route(
            self.normalized_path,
            endpoint,
            methods=["GET"],
            name=self.title,
            response_class=HTMLResponse,
        )


class PageDescriptorManager:
    """Coordinate admin, settings, and public page registrations."""

    def __init__(self, admin_site: "AdminSite") -> None:
        """Store ``admin_site`` and initialise descriptor collections."""

        self._admin_site = admin_site
        self._descriptors: Dict[str, PageDescriptor] = {}
        self._public_descriptors: List[PageDescriptor] = []
        self._public_router: APIRouter | None = None
        self._public_router_dirty = False

    @property
    def admin_site(self) -> "AdminSite":
        """Return the admin site the manager is bound to."""

        return self._admin_site

    @property
    def admin_auth_service(self):  # pragma: no cover - attribute proxy
        """Expose admin auth service from the owning site."""

        return getattr(self._admin_site, "admin_auth_service")

    @property
    def page_responder(self):  # pragma: no cover - attribute proxy
        """Return template responder used for public pages."""

        from .templates import PageTemplateResponder

        return PageTemplateResponder

    def register_view(
        self,
        *,
        path: str,
        name: str,
        icon: str | None = None,
        label: str | None = None,
        settings: bool | None = None,
        include_in_sidebar: bool = True,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register an administrative view page."""

        normalized_path = self._normalize_path(path)
        slug_source = normalized_path.strip("/")
        owning_label = label or (slug_source.split("/", 1)[0] if slug_source else None)
        if owning_label is None:
            owning_label = self._admin_site._model_to_slug(name)

        settings_prefix = system_config.get_cached(SettingsKey.SETTINGS_PREFIX, "/settings")
        views_prefix = system_config.get_cached(SettingsKey.VIEWS_PREFIX, "/views")
        orm_prefix = system_config.get_cached(SettingsKey.ORM_PREFIX, "/orm")

        derived_settings = settings
        if derived_settings is None:
            derived_settings = normalized_path.startswith(settings_prefix)

        normalized_key = self._normalize_key(normalized_path)
        section_prefixes = (
            self._normalize_prefix(views_prefix),
            self._normalize_prefix(orm_prefix),
            self._normalize_prefix(settings_prefix),
        )

        has_required_tail = True
        tail_segments: List[str] = []
        for section_prefix in section_prefixes:
            if normalized_key == section_prefix:
                has_required_tail = False
                break
            if normalized_key.startswith(f"{section_prefix}/"):
                tail = normalized_key[len(section_prefix) + 1 :]
                tail_segments = [segment for segment in tail.split("/") if segment]
                has_required_tail = len(tail_segments) >= 2
                break

        if not tail_segments and has_required_tail:
            tail_segments = [segment for segment in slug_source.split("/") if segment]

        app_segment: str | None = None
        normalized_segments = [
            self._admin_site._model_to_slug(segment) for segment in tail_segments
        ]
        if normalized_segments:
            app_segment = normalized_segments[0]
        if has_required_tail and app_segment is None and owning_label is not None:
            app_segment = self._admin_site._model_to_slug(owning_label)

        app_for_virtual = owning_label or app_segment or name
        slug_seed = slug_source or name
        virtual = self._admin_site.registry.register_view_virtual(
            path=normalized_path,
            app_label=str(app_for_virtual),
            slug_source=str(slug_seed),
        )
        if app_segment is None:
            app_segment = virtual.app_slug
        owning_label = owning_label or virtual.app_label

        section = self._classify_section(
            normalized_key,
            views_prefix,
            orm_prefix,
            settings_prefix,
        )
        model_name = (
            slug_source.replace("/", "_")
            if slug_source
            else self._admin_site._model_to_slug(name)
        )

        descriptor = PageDescriptor(
            manager=self,
            title=name,
            path=normalized_path,
            icon=icon,
            normalized_path=normalized_path,
            normalized_key=normalized_key,
            owning_label=owning_label,
            section=section,
            include_in_sidebar=include_in_sidebar,
            has_required_tail=has_required_tail,
            settings=bool(derived_settings),
            model_name=model_name,
            app_label=app_segment,
            app_slug=virtual.app_slug,
            slug=virtual.slug if virtual.slug else None,
            dotted=virtual.dotted,
            page_class=FreeViewPage,
        )
        self._descriptors[normalized_key] = descriptor

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return descriptor.bind_handler(func)

        return decorator

    def register_settings(
        self,
        *,
        path: str,
        name: str,
        icon: str | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a settings page under the settings section."""

        normalized_path = self._normalize_path(path)
        normalized_key = self._normalize_key(normalized_path)
        page_type_settings = system_config.get_cached(
            SettingsKey.PAGE_TYPE_SETTINGS, "settings"
        )
        settings_prefix = system_config.get_cached(SettingsKey.SETTINGS_PREFIX, "/settings")
        has_required_tail = (
            normalized_key
            != self._normalize_prefix(settings_prefix)
        )
        virtual = self._admin_site.registry.register_view_virtual(
            path=normalized_path,
            app_label="settings",
            slug_source=name,
        )

        descriptor = PageDescriptor(
            manager=self,
            title=name,
            path=normalized_path,
            icon=icon,
            normalized_path=normalized_path,
            normalized_key=normalized_key,
            owning_label=virtual.app_label,
            section="settings",
            include_in_sidebar=True,
            has_required_tail=has_required_tail,
            settings=True,
            model_name=virtual.slug,
            app_label=virtual.app_slug,
            app_slug=virtual.app_slug,
            slug=virtual.slug,
            dotted=virtual.dotted,
            page_class=SettingsPage,
            menu_page_type=page_type_settings,
        )
        self._descriptors[normalized_key] = descriptor

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return descriptor.bind_handler(func)

        return decorator

    def register_public_view(
        self,
        *,
        path: str,
        name: str,
        template: str,
        icon: str | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a public page rendered outside the admin shell."""

        normalized_path = self._normalize_path(path)
        normalized_key = self._normalize_key(normalized_path)
        descriptor = PageDescriptor(
            manager=self,
            title=name,
            path=normalized_path,
            icon=icon,
            normalized_path=normalized_path,
            normalized_key=normalized_key,
            owning_label=name,
            section="public",
            include_in_sidebar=False,
            has_required_tail=False,
            settings=False,
            model_name=name,
            app_label=None,
            app_slug=None,
            slug=None,
            dotted=None,
            page_class=FreeViewPage,
            template_name=template,
            public=True,
        )
        self._public_descriptors.append(descriptor)
        self._public_router_dirty = True
        self._admin_site.public_menu_builder.register_item(
            title=name,
            path=normalized_path,
            icon=icon,
        )

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            descriptor.handler = func
            return func

        return decorator

    def iter_sidebar_views(
        self, *, settings: bool
    ) -> List[Tuple[str, List[Dict[str, Any]]]]:
        """Return sidebar groupings for registered views."""

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for descriptor in self._descriptors.values():
            if descriptor.public:
                continue
            if not descriptor.include_in_sidebar or not descriptor.has_required_tail:
                continue
            if descriptor.settings != settings:
                continue
            grouped.setdefault(descriptor.owning_label, []).append(
                descriptor.build_sidebar_entry()
            )

        items: List[Tuple[str, List[Dict[str, Any]]]] = []
        for label, entries in grouped.items():
            entries.sort(key=lambda item: item["display_name"].lower())
            items.append((label, entries))
        items.sort(key=lambda item: item[0].lower())
        return items

    def resolve_request(self, request: Request) -> PageResolution:
        """Analyse ``request`` to determine the active navigation context."""

        admin_prefix = system_config.get_cached(
            SettingsKey.ADMIN_PREFIX, self._admin_site._settings.admin_path
        ).rstrip("/")
        trimmed_path = request.url.path
        if admin_prefix and trimmed_path.startswith(admin_prefix):
            trimmed_path = trimmed_path[len(admin_prefix) :]
            if not trimmed_path.startswith("/"):
                trimmed_path = f"/{trimmed_path}"

        normalized_path = trimmed_path.rstrip("/") or "/"
        views_prefix = system_config.get_cached(SettingsKey.VIEWS_PREFIX, "/views")
        orm_prefix = system_config.get_cached(SettingsKey.ORM_PREFIX, "/orm")
        settings_prefix = system_config.get_cached(SettingsKey.SETTINGS_PREFIX, "/settings")
        normalized_views = self._normalize_prefix(views_prefix)
        normalized_orm = self._normalize_prefix(orm_prefix)
        normalized_settings = self._normalize_prefix(settings_prefix)

        section_mode = "orm"
        if normalized_path == normalized_settings or normalized_path.startswith(
            f"{normalized_settings}/"
        ):
            section_mode = "settings"
        elif normalized_path == normalized_orm or normalized_path.startswith(
            f"{normalized_orm}/"
        ):
            section_mode = "orm"
        elif normalized_path == normalized_views or normalized_path.startswith(
            f"{normalized_views}/"
        ):
            section_mode = "views"

        is_settings = section_mode == "settings"
        app_label: Optional[str] = None
        model_slug: Optional[str] = None

        segments = [
            segment for segment in normalized_path.strip("/").split("/") if segment
        ]
        if section_mode in {"orm", "settings"} and len(segments) >= 2:
            app_label = segments[1]
            if len(segments) >= 3:
                model_slug = segments[2]

        descriptor = self._descriptors.get(normalized_path)
        if descriptor is not None:
            section_mode = descriptor.section
            if descriptor.settings:
                is_settings = True
            if descriptor.app_label:
                app_label = descriptor.app_label
            if descriptor.slug:
                model_slug = descriptor.slug

        return PageResolution(
            normalized_path=normalized_path,
            section_mode=section_mode,
            is_settings=is_settings,
            app_label=app_label,
            model_slug=model_slug,
            descriptor=descriptor,
        )

    def attach_admin_routes(
        self,
        router: APIRouter,
        *,
        templates,
        page_type_settings: str,
        views_prefix: str,
        settings_prefix: str,
        orm_prefix: str,
    ) -> None:
        """Mount registered admin pages onto ``router``."""

        for descriptor in list(self._descriptors.values()):
            if descriptor.public:
                continue
            descriptor.mount_admin_route(
                router,
                templates=templates,
                page_type_settings=page_type_settings,
                views_prefix=views_prefix,
                settings_prefix=settings_prefix,
                orm_prefix=orm_prefix,
            )

    def iter_public_routers(self) -> Iterable[APIRouter]:
        """Yield routers exposing registered public pages."""

        if not self._public_descriptors:
            return ()
        if self._public_router is None or self._public_router_dirty:
            router = APIRouter()
            for descriptor in self._public_descriptors:
                descriptor.mount_public_route(router)
            self._public_router = router
            self._public_router_dirty = False
        return (self._public_router,)

    @staticmethod
    def _normalize_path(path: str) -> str:
        return path if path.startswith("/") else f"/{path}"

    @staticmethod
    def _normalize_key(path: str) -> str:
        return path.rstrip("/") or "/"

    @staticmethod
    def _normalize_prefix(prefix: str) -> str:
        cleaned = prefix if prefix.startswith("/") else f"/{prefix}"
        return cleaned.rstrip("/") or "/"

    def _classify_section(
        self,
        normalized_key: str,
        views_prefix: str,
        orm_prefix: str,
        settings_prefix: str,
    ) -> str:
        normalized_views = self._normalize_prefix(views_prefix)
        normalized_orm = self._normalize_prefix(orm_prefix)
        normalized_settings = self._normalize_prefix(settings_prefix)
        if normalized_key == normalized_settings or normalized_key.startswith(
            f"{normalized_settings}/"
        ):
            return "settings"
        if normalized_key == normalized_orm or normalized_key.startswith(
            f"{normalized_orm}/"
        ):
            return "orm"
        return "views"

# The End
