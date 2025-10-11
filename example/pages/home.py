# -*- coding: utf-8 -*-
"""Example standalone pages for the FreeAdmin demo."""

from __future__ import annotations

from fastapi import Request

from freeadmin.core.services.auth import AdminUserDTO
from freeadmin.hub import admin_site


class ExampleWelcomePage:
    """Register a welcome page showcasing custom admin content."""

    path = "/example/welcome"
    name = "Welcome"
    label = "Example"
    icon = "bi-stars"

    def __init__(self) -> None:
        """Store helpers required for page registration."""

        self._site = admin_site

    def register(self) -> None:
        """Attach the welcome page handler to the admin site."""

        @self._site.register_view(
            path=self.path,
            name=self.name,
            label=self.label,
            icon=self.icon,
        )
        async def welcome_page(
            request: Request, user: AdminUserDTO
        ) -> dict[str, object]:
            return self._site.build_template_ctx(
                request,
                user,
                page_message="Welcome to the FreeAdmin example!",
                card_entries=[],
            )

        self._handler = welcome_page


example_welcome_page = ExampleWelcomePage()
example_welcome_page.register()

__all__ = ["ExampleWelcomePage", "example_welcome_page"]

# The End

