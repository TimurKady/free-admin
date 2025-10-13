# -*- coding: utf-8 -*-
"""Admin views and card registration for the demo app."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from freeadmin.boot import admin as boot_admin
from freeadmin.core.services.auth import AdminUserDTO
from freeadmin.hub import admin_site


class DemoTemperatureCard:
    """Manage registration of the thermometer card."""

    key = "thermo1"
    label = "Demo"
    title = "Temperature Sensor"
    template = "cards/thermo.html"
    icon = "bi-thermometer-half"
    channel = "sensor:temp"

    def __init__(self) -> None:
        """Store references required for card registration."""
        self._site = admin_site

    def register(self) -> None:
        """Register the temperature card with the admin site."""
        self._site.register_card(
            key=self.key,
            label=self.label,
            title=self.title,
            template=self.template,
            icon=self.icon,
            channel=self.channel,
        )


class DemoHelloView:
    """Expose a standalone hello view with user statistics."""

    path = "/demo/hello"
    name = "Hello world!"
    icon = "bi-person-check"
    label = "Demo"
    assets = {"js": ("js/demo-hello.js",), "css": ()}

    def __init__(self) -> None:
        """Prepare the hello view registrar and data dependencies."""
        self._site = admin_site
        self._user_model = boot_admin.user_model
        self._assets = {
            "js": tuple(self.assets.get("js", ())),
            "css": tuple(self.assets.get("css", ())),
        }

    def register(self) -> None:
        """Attach the hello view handler to the admin site."""

        @self._site.register_view(
            path=self.path,
            name=self.name,
            icon=self.icon,
            label=self.label,
        )
        async def hello_demo_view(
            request: Request,
            user: AdminUserDTO,
        ) -> dict[str, Any]:
            count = await self._fetch_user_count()
            return {
                "page_message": self._format_message(count),
                "card_entries": [],
                "assets": self._assets_payload(),
            }

        self._handler = hello_demo_view

    async def _fetch_user_count(self) -> int:
        model = self._user_model
        if model is None:
            return 0
        return await model.all().count()

    def _format_message(self, count: int) -> str:
        return f"Hello world! Registered users: {count}"

    def _assets_payload(self) -> dict[str, tuple[str, ...]]:
        """Return a context-safe copy of the declared assets."""
        return {
            "js": tuple(self._assets.get("js", ())),
            "css": tuple(self._assets.get("css", ())),
        }


class DemoDashboard:
    """Configure the demo admin view together with its card."""

    _is_registered: bool = False

    def __init__(self) -> None:
        """Register demo showcase components once during initialization."""
        if not self.__class__._is_registered:
            self._card = DemoTemperatureCard()
            self._view = DemoHelloView()
            self._card.register()
            self._view.register()
            self.__class__._is_registered = True


demo_dashboard = DemoDashboard()

__all__ = ["DemoDashboard", "demo_dashboard"]

# The End

