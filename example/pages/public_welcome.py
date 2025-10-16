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

from freeadmin.core.interface.pages import BaseTemplatePage
from freeadmin.core.runtime.hub import admin_site


class ExamplePublicWelcomeContext(BaseTemplatePage):
    """Register the example public welcome page with the admin site."""

    path = "/"
    name = "Welcome"
    template = "pages/welcome.html"
    template_directory = Path(__file__).resolve().parent.parent / "templates"

    def __init__(self) -> None:
        """Register the public welcome view when instantiated."""

        super().__init__(site=admin_site)
        self.register_public_view()

    async def get_context(
        self,
        *,
        request: Request,
        user: object | None = None,
    ) -> dict[str, object]:
        """Return template context for the welcome example page."""

        return {
            "subtitle": "Rendered outside the admin",
            "user": user,
        }


example_public_welcome_context = ExamplePublicWelcomeContext()


# The End


