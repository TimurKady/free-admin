# -*- coding: utf-8 -*-
"""
routers

Route assembly helpers for the FreeAdmin example project.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from collections.abc import Iterable

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, RedirectResponse

from freeadmin.api.cards import public_router as card_public_router
from freeadmin.core.settings import SettingsKey, system_config
from freeadmin.hub import admin_site
from freeadmin.router import RouterAggregator


class ExampleRouterAggregator(RouterAggregator):
    """Attach admin, card, and public routes to the demo application."""

    def __init__(self) -> None:
        """Initialise the example router aggregator with default routes."""

        super().__init__(admin_site)
        self._card_router = card_public_router
        self._public_router = self._create_public_router()

    @property
    def card_router(self) -> APIRouter:
        """Return the router exposing card endpoints to the public."""

        return self._card_router

    @property
    def public_router(self) -> APIRouter:
        """Return the router exposing public redirect endpoints."""

        return self._public_router

    def get_additional_routers(self) -> Iterable[tuple[APIRouter, str | None]]:
        """Return card and public routers to mount alongside the admin site."""

        yield from super().get_additional_routers()
        yield self.card_router, None
        yield self.public_router, None

    def _create_public_router(self) -> APIRouter:
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
