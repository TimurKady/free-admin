# -*- coding: utf-8 -*-
"""
test_example_application

Smoke tests that validate the example application setup.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from example.config.main import ExampleApplication
from tests.sampleapp.app import default as sample_app_config


class TestExampleApplicationSmoke:
    """Verify that the example application mounts the admin router."""

    def test_admin_router_mounted(self) -> None:
        """Ensure configuring the example attaches the admin site to the app."""

        application = ExampleApplication()
        app = application.configure()

        assert getattr(app.state, "admin_site", None) is not None


class TestExampleApplicationStartup:
    """Ensure application configs execute startup hooks during boot."""

    @pytest.mark.asyncio
    async def test_app_config_startup_called(self) -> None:
        """Verify AppConfig.startup executes when FastAPI starts up."""

        sample_app_config.ready_calls = 0
        application = ExampleApplication()
        application.register_packages(["tests.sampleapp"])
        app = application.configure()

        boot_manager = application.boot_manager
        hub = boot_manager._ensure_hub()
        hub.admin_site.finalize = AsyncMock()
        hub.admin_site.cards.start_publishers = AsyncMock()
        hub.admin_site.cards.shutdown_publishers = AsyncMock()
        boot_manager._config = SimpleNamespace(
            ensure_seed=AsyncMock(),
            reload=AsyncMock(),
        )

        await app.router.startup()
        try:
            assert sample_app_config.ready_calls == 1
        finally:
            await app.router.shutdown()


# The End

