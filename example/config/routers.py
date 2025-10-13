# -*- coding: utf-8 -*-
"""
routers

Route assembly helpers for the FreeAdmin example project.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from typing import Optional, Type

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from starlette import status

from freeadmin.api.cards import public_router
from freeadmin.core.settings import SettingsKey, system_config
from freeadmin.router import AdminRouter


class ExampleAdminRedirectResponder:
    """Return redirect responses that respect the configured admin prefix."""

    def __init__(
        self,
        *,
        path_key: Optional[SettingsKey] = None,
        status_code: int = status.HTTP_307_TEMPORARY_REDIRECT,
    ) -> None:
        """Store the target configuration used when crafting redirects."""

        self._path_key = path_key
        self._status_code = status_code

    async def __call__(self, request: Request | None = None) -> RedirectResponse:
        """Build a redirect pointing to the configured admin endpoint."""

        admin_prefix = await system_config.get(
            SettingsKey.ADMIN_PREFIX, "/admin"
        )
        if self._path_key is None:
            target = admin_prefix
            if not target.endswith("/"):
                target = f"{target}/"
        else:
            suffix = await system_config.get(self._path_key, "")
            target = f"{admin_prefix}{suffix}"
        return RedirectResponse(target, status_code=self._status_code)


class ExampleRobotsResponder:
    """Return the robots.txt directives managed by the system configuration."""

    def __init__(self) -> None:
        """Instantiate the responder without additional state."""

    async def __call__(self) -> PlainTextResponse:
        """Return the current robots directives as a plain text response."""

        directives = await system_config.get(
            SettingsKey.ROBOTS_DIRECTIVES,
            "User-agent: *\nDisallow: /\n",
        )
        return PlainTextResponse(directives, media_type="text/plain")


class ExampleAdminRouters:
    """Configure HTTP routes for the FreeAdmin example application."""

    def __init__(self, *, admin_router_cls: Type[AdminRouter] = AdminRouter) -> None:
        """Prepare reusable routers for redirects and metadata endpoints."""

        self._admin_router_cls = admin_router_cls
        self._home_router = APIRouter()
        self._auth_router = APIRouter()
        self._meta_router = APIRouter()
        self._public_router = public_router
        self._configure_home()
        self._configure_auth()
        self._configure_metadata()

    def attach_to(self, app: FastAPI) -> None:
        """Register the example routers on ``app``."""

        app.include_router(self._home_router)
        app.include_router(self._auth_router)
        app.include_router(self._meta_router)
        app.include_router(self._public_router)

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------
    def _configure_home(self) -> None:
        responder = ExampleAdminRedirectResponder()
        self._home_router.add_api_route(
            "/",
            responder,
            methods=["GET"],
            include_in_schema=False,
            name="example-admin-home",
        )

    def _configure_auth(self) -> None:
        login_path = system_config.get_cached(SettingsKey.LOGIN_PATH, "/login")
        logout_path = system_config.get_cached(SettingsKey.LOGOUT_PATH, "/logout")
        login_responder = ExampleAdminRedirectResponder(
            path_key=SettingsKey.LOGIN_PATH
        )
        logout_responder = ExampleAdminRedirectResponder(
            path_key=SettingsKey.LOGOUT_PATH
        )
        self._auth_router.add_api_route(
            login_path,
            login_responder,
            methods=["GET"],
            include_in_schema=False,
            name="example-admin-login",
        )
        self._auth_router.add_api_route(
            logout_path,
            logout_responder,
            methods=["GET"],
            include_in_schema=False,
            name="example-admin-logout",
        )

    def _configure_metadata(self) -> None:
        responder = ExampleRobotsResponder()
        self._meta_router.add_api_route(
            "/robots.txt",
            responder,
            methods=["GET"],
            include_in_schema=False,
            response_class=PlainTextResponse,
            name="example-robots",
        )


__all__ = ["ExampleAdminRouters", "ExampleAdminRedirectResponder", "ExampleRobotsResponder"]


# The End

