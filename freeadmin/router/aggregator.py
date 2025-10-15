# -*- coding: utf-8 -*-
"""
router.aggregator

Coordinator for creating, caching, and mounting admin routers.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from weakref import WeakSet

from fastapi import APIRouter, FastAPI, Request

from ..conf import FreeAdminSettings, current_settings
from ..core.settings import SettingsKey, system_config
from ..core.site import AdminSite
from ..provider import TemplateProvider

ASSETS_DIR = Path(__file__).resolve().parent.parent / "static"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class RouterAggregator:
    """Coordinate creation and mounting of admin routers."""

    def __init__(
        self,
        site: AdminSite,
        prefix: str | None = None,
        *,
        settings: FreeAdminSettings | None = None,
        additional_routers: Iterable[tuple[APIRouter, str | None]] | None = None,
    ) -> None:
        """Initialise the aggregator with the admin site and base settings."""

        self.site = site
        self._settings = settings or current_settings()
        default_prefix = system_config.get_cached(
            SettingsKey.ADMIN_PREFIX, self._settings.admin_path
        )
        self._prefix = (prefix or default_prefix).rstrip("/")
        self._provider = TemplateProvider(
            templates_dir=str(TEMPLATES_DIR),
            static_dir=str(ASSETS_DIR),
            settings=self._settings,
        )
        self._admin_router: APIRouter | None = None
        self._mounted_apps: WeakSet[FastAPI] = WeakSet()
        self._additional_routers: list[tuple[APIRouter, str | None]] = list(
            additional_routers or ()
        )

    @property
    def prefix(self) -> str:
        """Return the current prefix used for mounting the admin router."""

        return self._prefix

    def create_admin_router(self) -> APIRouter:
        """Instantiate the FastAPI router for the admin site."""

        return self.site.build_router(self._provider)

    def get_admin_router(self) -> APIRouter:
        """Return the cached admin router, creating it when necessary."""

        if self._admin_router is None:
            self._admin_router = self.create_admin_router()
        return self._admin_router

    def mount(self, app: FastAPI, prefix: str | None = None) -> None:
        """Mount the admin router and any configured extras onto the app."""

        self._prefix = (prefix or self._prefix).rstrip("/")
        self._ensure_templates()
        app.state.admin_site = self.site
        if app in self._mounted_apps:
            return

        router = self.get_admin_router()
        app.include_router(router, prefix=self._prefix)
        self._provider.mount_static(app, self._prefix)
        self._provider.mount_favicon(app)
        self._provider.mount_media(app)
        self.register_additional_routers(app)
        self._mounted_apps.add(app)

    def register_additional_routers(self, app: FastAPI) -> None:
        """Register optional routers configured for the aggregator."""

        for router, router_prefix in self._iter_additional_routers():
            app.include_router(router, prefix=router_prefix or "")

    def add_additional_router(
        self, router: APIRouter, prefix: str | None = None
    ) -> None:
        """Register ``router`` so it is mounted alongside the admin router."""

        self._additional_routers.append((router, prefix))

    def get_additional_routers(self) -> Iterable[tuple[APIRouter, str | None]]:
        """Return routers that should be mounted alongside the admin router."""

        return ()

    def _iter_additional_routers(self) -> Iterable[tuple[APIRouter, str | None]]:
        yield from self._additional_routers
        if self.__class__.get_additional_routers is not RouterAggregator.get_additional_routers:  # type: ignore[misc]
            yield from self.get_additional_routers()

    def _ensure_templates(self) -> None:
        if self.site.templates is None:
            self.site.templates = self._provider.get_templates()



class ExtendedRouterAggregator(RouterAggregator):
    """Compose admin and public routers within a single aggregator."""

    def __init__(
        self,
        site: AdminSite,
        prefix: str | None = None,
        *,
        settings: FreeAdminSettings | None = None,
        additional_routers: Iterable[tuple[APIRouter, str | None]] | None = None,
        public_first: bool = True,
    ) -> None:
        """Initialise the aggregator and configure registration order."""

        super().__init__(
            site=site,
            prefix=prefix,
            settings=settings,
            additional_routers=additional_routers,
        )
        self._public_first = public_first
        self._public_routers: list[APIRouter] = []
        self._router: APIRouter | None = None
        retained: list[tuple[APIRouter, str | None]] = []
        for router, router_prefix in self._additional_routers:
            if router_prefix in (None, ""):
                self._public_routers.append(router)
            else:
                retained.append((router, router_prefix))
        self._additional_routers = retained

    def add_admin_router(
        self, router: APIRouter, prefix: str | None = None
    ) -> None:
        """Register ``router`` so it is exposed under the admin prefix."""

        super().add_additional_router(router, prefix or self.prefix)
        self._invalidate_router_cache()

    def add_additional_router(
        self, router: APIRouter, prefix: str | None = None
    ) -> None:
        """Register ``router`` without a prefix for public exposure."""

        if prefix not in (None, ""):
            super().add_additional_router(router, prefix)
        else:
            self._public_routers.append(router)
        self._invalidate_router_cache()

    def get_routers(self) -> list[tuple[APIRouter, str | None]]:
        """Return all registered routers respecting the configured order."""

        self._ensure_templates()
        admin_entries = self._collect_admin_entries()
        public_entries = [(router, None) for router in self._public_routers]
        if self._public_first:
            return [*public_entries, *admin_entries]
        return [*admin_entries, *public_entries]

    def mount(self, app: FastAPI, prefix: str | None = None) -> None:
        """Mount public and admin routers onto ``app`` respecting order."""

        self._prefix = (prefix or self._prefix).rstrip("/")
        self._ensure_templates()
        app.state.admin_site = self.site
        if app in self._mounted_apps:
            return

        for router, router_prefix in self.get_routers():
            app.include_router(router, prefix=router_prefix or "")
        self._provider.mount_static(app, self._prefix)
        self._provider.mount_favicon(app)
        self._provider.mount_media(app)
        self._mounted_apps.add(app)

    @property
    def router(self) -> APIRouter:
        """Return an ``APIRouter`` aggregating all registered routers."""

        if self._router is None:
            aggregated = APIRouter()

            @aggregated.middleware("http")
            async def ensure_admin_state(request: Request, call_next):  # type: ignore[unused-ignore]
                if getattr(request.app.state, "admin_site", None) is None:
                    request.app.state.admin_site = self.site
                return await call_next(request)

            for router, router_prefix in self.get_routers():
                aggregated.include_router(router, prefix=router_prefix or "")
            self._router = aggregated
        return self._router

    def _collect_admin_entries(self) -> list[tuple[APIRouter, str | None]]:
        entries: list[tuple[APIRouter, str | None]] = [
            (self.get_admin_router(), self.prefix)
        ]
        entries.extend(self._additional_routers)
        if (
            self.__class__.get_additional_routers
            is not RouterAggregator.get_additional_routers  # type: ignore[misc]
        ):
            entries.extend(self.get_additional_routers())
        return entries

    def _invalidate_router_cache(self) -> None:
        self._router = None


# The End


