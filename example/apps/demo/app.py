# -*- coding: utf-8 -*-
"""Demo application bootstrap configuration."""

from __future__ import annotations

from ..base import ExampleAppConfig
from freeadmin.hub import admin_site

from .service import TemperaturePublisher
from .views import DemoDashboard


class DemoConfig(ExampleAppConfig):
    """Initialize demo dashboard resources for the admin panel."""

    app_label = "demo"
    name = "freeadmin.example.apps.demo"

    def __init__(self) -> None:
        """Instantiate helpers required for the demo showcase."""

        super().__init__()
        self.dashboard = DemoDashboard()
        self.publisher = TemperaturePublisher()

    async def startup(self) -> None:
        """Register the demo publisher so card updates become active."""

        admin_site.cards.register_publisher(self.publisher)


default = DemoConfig()

__all__ = ["DemoConfig", "default"]

# The End

