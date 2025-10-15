# -*- coding: utf-8 -*-
"""
routers

Route assembly helpers for the FreeAdmin example project.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, RedirectResponse

from example.pages import public_welcome_router
from freeadmin.api.cards import public_router as card_public_router
from freeadmin.core.interface.settings import SettingsKey, system_config
from freeadmin.core.runtime.hub import admin_site
from freeadmin.core.network.router import RouterAggregator


class ExampleRouterAggregator(RouterAggregator):
    """Attach admin, card, and public routes to the demo application."""

    def __init__(self) -> None:
        """Initialise the example router aggregator with default routes."""

        super().__init__(admin_site)
        self.add_additional_router(card_public_router, None)
        self.add_additional_router(public_welcome_router, None)
        self.add_additional_router(self.create_public_router(), None)

    def create_public_router(self) -> APIRouter:
        """Build the public router exposed by the example project."""

        router = APIRouter()
        login_path = system_config.get_cached(SettingsKey.LOGIN_PATH, "/login")
        logout_path = system_config.get_cached(SettingsKey.LOGOUT_PATH, "/logout")
        robots_path = "/robots.txt"

        @router.get(login_path, include_in_schema=False)
        async def login_redirect() -> RedirectResponse:
            """Redirect visitors to the admin login page."""

            admin_prefix = await system_config.get(
                SettingsKey.ADMIN_PREFIX, "/admin"
            )
            return RedirectResponse(
                f"{admin_prefix}{login_path}", status_code=303
            )

        @router.get(logout_path, include_in_schema=False)
        async def logout_redirect() -> RedirectResponse:
            """Redirect visitors to the admin logout endpoint."""

            admin_prefix = await system_config.get(
                SettingsKey.ADMIN_PREFIX, "/admin"
            )
            return RedirectResponse(
                f"{admin_prefix}{logout_path}", status_code=303
            )

        @router.get(
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

        return router


ExampleAdminRouters = ExampleRouterAggregator

__all__ = [
    "ExampleRouterAggregator",
    "ExampleAdminRouters",
]


# The End
