# -*- coding: utf-8 -*-
"""
example.pages.welcome_page

Example public page demonstrating FreeAdmin's extended router aggregator.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from example.rendering import ExampleTemplateRenderer


class ExamplePublicWelcomePage:
    """Expose a public welcome page mounted at the site root."""

    path = "/"

    def __init__(self) -> None:
        """Initialise and register the public welcome page router."""

        self._router = APIRouter()
        self._handler: object | None = None
        self._register_routes()

    def get_router(self) -> APIRouter:
        """Return the router that serves the public welcome page."""

        return self._router

    def get_handler(self) -> object | None:
        """Return the registered handler for the public welcome page."""

        return self._handler

    def _register_routes(self) -> None:
        """Register HTTP routes for the public welcome page."""

        @self._router.get(self.path, response_class=HTMLResponse)
        async def index(request: Request) -> HTMLResponse:
            return self._render_response(request)

        self._handler = index

    def _render_response(self, request: Request) -> HTMLResponse:
        """Render the welcome template for anonymous visitors."""

        context = {"title": "Welcome", "user": None}
        return ExampleTemplateRenderer.render(
            "welcome.html", context, request=request
        )


example_public_welcome_page = ExamplePublicWelcomePage()
public_welcome_router = example_public_welcome_page.get_router()


# The End


