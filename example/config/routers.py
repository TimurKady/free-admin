# -*- coding: utf-8 -*-
"""
routers

Route assembly helpers for the FreeAdmin example project.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.responses import PlainTextResponse, RedirectResponse

from freeadmin.api.cards import public_router as card_public_router
from freeadmin.core.settings import SettingsKey, system_config
from freeadmin.hub import admin_site
from freeadmin.router import AdminRouter


class ExampleRouterAggregator:
    """Attach admin, card, and public routes to the demo application."""

    def __init__(self) -> None:
        """Set up router instances ready to mount on an application."""

        self._admin_router = AdminRouter(admin_site)
        self._card_router = card_public_router
        self._public_router = APIRouter()
        self._configure_public_routes()

    def _configure_public_routes(self) -> None:
        login_path = system_config.get_cached(SettingsKey.LOGIN_PATH, "/login")
        logout_path = system_config.get_cached(SettingsKey.LOGOUT_PATH, "/logout")
        robots_path = "/robots.txt"

        @self._public_router.get(login_path, include_in_schema=False)
        async def login_redirect() -> RedirectResponse:
            """Redirect visitors to the admin login page."""

            admin_prefix = await system_config.get(
                SettingsKey.ADMIN_PREFIX, "/admin"
            )
            return RedirectResponse(
                f"{admin_prefix}{login_path}", status_code=303
            )

        @self._public_router.get(logout_path, include_in_schema=False)
        async def logout_redirect() -> RedirectResponse:
            """Redirect visitors to the admin logout endpoint."""

            admin_prefix = await system_config.get(
                SettingsKey.ADMIN_PREFIX, "/admin"
            )
            return RedirectResponse(
                f"{admin_prefix}{logout_path}", status_code=303
            )

        @self._public_router.get(
            robots_path,
            include_in_schema=False,
            response_class=PlainTextResponse,
        )
        async def robots_txt() -> PlainTextResponse:
            """Serve robots.txt directives derived from system settings."""

            directives = await system_config.get(
                SettingsKey.ROBOTS_DIRECTIVES,
                "User-agent: *\nDisallow: /\n",
            )
            return PlainTextResponse(directives)

    def mount(self, app: FastAPI) -> None:
        """Include the admin and supporting routers on ``app``."""

        if getattr(app.state, "admin_site", None) is None:
            self._admin_router.mount(app)
        app.include_router(self._card_router)
        app.include_router(self._public_router)


__all__ = ["ExampleRouterAggregator"]


# The End
