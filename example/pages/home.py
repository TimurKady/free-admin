# -*- coding: utf-8 -*-
"""Example standalone pages for the FreeAdmin demo."""

from __future__ import annotations

from fastapi import Request

from freeadmin.core.interface.pages import BaseTemplatePage
from freeadmin.core.interface.services.auth import AdminUserDTO
from freeadmin.core.runtime.hub import admin_site


class ExampleWelcomePage(BaseTemplatePage):
    """Register a welcome page showcasing custom admin content."""

    path = "/example/welcome"
    name = "Welcome"
    label = "Example"
    icon = "bi-stars"

    def __init__(self) -> None:
        """Initialise the welcome page and register it with the admin site."""

        super().__init__(site=admin_site)
        self.register_admin_view()

    async def get_context(
        self,
        *,
        request: Request,
        user: AdminUserDTO | None = None,
    ) -> dict[str, object]:
        """Return context for the admin welcome page."""

        return {
            "page_message": "Welcome to the FreeAdmin example!",
            "card_entries": [],
        }


example_welcome_page = ExampleWelcomePage()

__all__ = ["ExampleWelcomePage", "example_welcome_page"]

# The End

