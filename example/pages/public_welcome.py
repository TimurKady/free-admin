# -*- coding: utf-8 -*-
"""
example.pages.public_welcome

Example public page demonstrating FreeAdmin's extended router aggregator.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from pathlib import Path

from fastapi import Request

from freeadmin.core.runtime.hub import admin_site
from freeadmin.core.interface.templates import TemplateRenderer


class ExamplePublicWelcomeContext:
    """Register the example public welcome page with the admin site."""

    path = "/"
    name = "Welcome"
    template = "pages/welcome.html"
    template_directory = Path(__file__).resolve().parent.parent / "templates"

    def __init__(self) -> None:
        """Register the public welcome view when the context helper is created."""

        self._ensure_template_registration()
        admin_site.register_public_view(
            path=self.path,
            name=self.name,
            template=self.template,
        )(self.render_context)

    async def render_context(
        self, request: Request, user: object | None = None
    ) -> dict[str, object]:
        """Return template context for the welcome example page."""

        return {
            "subtitle": "Rendered outside the admin",
            "user": user,
        }

    def _ensure_template_registration(self) -> None:
        """Register example templates with the shared template renderer."""

        service = TemplateRenderer.get_service()
        service.add_template_directory(self.template_directory)


example_public_welcome_context = ExamplePublicWelcomeContext()


# The End


